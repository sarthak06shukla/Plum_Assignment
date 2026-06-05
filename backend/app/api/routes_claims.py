import logging
import subprocess
import sys
from threading import Lock
from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_current_user
from backend.app.db.session import SessionLocal, get_db
from backend.app.models.entities import (
    Claim,
    ClaimStatus,
    DecisionLog,
    Document,
    DocumentType,
    ManualReview,
    User,
    UserRole,
    utcnow,
)
from backend.app.schemas.claim import ClaimDetail, ClaimSummary, ProcessingStage
from backend.app.services.audit_service import AuditService
from backend.app.services.storage_service import DocumentUploadService, UploadValidationError


router = APIRouter(prefix="/claims", tags=["Claims"])
storage = DocumentUploadService()
audit = AuditService()
logger = logging.getLogger(__name__)
processing_claim_ids: set[str] = set()
processing_lock = Lock()


@router.post("", response_model=ClaimDetail)
async def submit_claim(
    prescription: Annotated[UploadFile, File()],
    medical_bill: Annotated[UploadFile, File()],
    diagnostic_report: Annotated[UploadFile | None, File()] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClaimDetail:
    claim = Claim(user_id=user.id, processing_stage="Files Uploaded")
    db.add(claim)
    db.flush()

    uploads = [
        (DocumentType.PRESCRIPTION, prescription),
        (DocumentType.MEDICAL_BILL, medical_bill),
    ]
    if diagnostic_report:
        uploads.append((DocumentType.DIAGNOSTIC_REPORT, diagnostic_report))

    try:
        for document_type, upload in uploads:
            path, size, mime = await storage.validate_and_store(upload, claim.id, document_type.value)
            db.add(
                Document(
                    claim_id=claim.id,
                    document_type=document_type,
                    filename=upload.filename or path.name,
                    storage_path=str(path),
                    mime_type=mime,
                    file_size=size,
                )
            )
    except UploadValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    claim.status = ClaimStatus.PROCESSING
    claim.processing_stage = "OCR Processing"
    claim.updated_at = utcnow()
    audit.log(db, actor_id=user.id, entity_type="Claim", entity_id=claim.id, action="SUBMIT_CLAIM", payload={})
    db.commit()
    db.refresh(claim)
    enqueue_claim_processing(claim.id)
    return serialize_claim_detail(claim)


def enqueue_claim_processing(claim_id: str) -> None:
    with processing_lock:
        if claim_id in processing_claim_ids:
            return
        processing_claim_ids.add(claim_id)
    try:
        completed = subprocess.Popen(
            [sys.executable, "-m", "backend.app.workers.process_claim", claim_id],
            stdout=None,
            stderr=None,
        )
    except Exception as exc:
        logger.exception("Could not start claim processor subprocess for %s: %s", claim_id, exc)
        with processing_lock:
            processing_claim_ids.discard(claim_id)
        _mark_claim_processing_failed(claim_id)
        return

    logger.info("Started claim processor subprocess pid=%s claim_id=%s", completed.pid, claim_id)
    _forget_claim_when_process_exits(claim_id, completed)


def _forget_claim_when_process_exits(claim_id: str, completed: subprocess.Popen) -> None:
    import threading

    def wait_for_exit() -> None:
        return_code = completed.wait()
        if return_code != 0:
            logger.error("Claim processor subprocess exited with code=%s claim_id=%s", return_code, claim_id)
        with processing_lock:
            processing_claim_ids.discard(claim_id)

    threading.Thread(target=wait_for_exit, daemon=True).start()


def _mark_claim_processing_failed(claim_id: str) -> None:
    db = SessionLocal()
    try:
        claim = db.get(Claim, claim_id)
        if not claim:
            return
        claim.status = ClaimStatus.MANUAL_REVIEW
        claim.processing_stage = "Decision Generation"
        claim.approved_amount = 0
        claim.confidence_score = 0
        claim.updated_at = utcnow()
        db.add(
            DecisionLog(
                claim_id=claim.id,
                decision=ClaimStatus.MANUAL_REVIEW.value,
                triggered_rule="PROCESSING_FAILED",
                explanation="Automated claim processing failed after upload.",
                notes=["The documents were uploaded, but OCR or extraction failed. Manual review is required."],
            )
        )
        db.add(ManualReview(claim_id=claim.id, reason="Automated claim processing failed after upload."))
        db.commit()
    finally:
        db.close()


@router.get("", response_model=list[ClaimSummary])
def list_claims(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ClaimSummary]:
    rows = db.scalars(select(Claim).where(Claim.user_id == user.id).order_by(Claim.created_at.desc())).all()
    for claim in rows:
        ensure_processing_started(db, claim)
    return [serialize_claim_summary(claim) for claim in rows]


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ClaimDetail:
    claim = db.get(Claim, claim_id)
    if not claim or (claim.user_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Claim not found")
    ensure_processing_started(db, claim)
    return serialize_claim_detail(claim)


@router.get("/{claim_id}/processing", response_model=list[ProcessingStage])
def get_processing(claim_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ProcessingStage]:
    claim = db.get(Claim, claim_id)
    if not claim or (claim.user_id != user.id and user.role != UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Claim not found")
    ensure_processing_started(db, claim)
    return processing_stages(claim)


def ensure_processing_started(db: Session, claim: Claim) -> None:
    if claim.status not in {ClaimStatus.SUBMITTED, ClaimStatus.PROCESSING}:
        return
    if not claim.documents:
        return
    if claim.decision_logs or claim.extracted_fields:
        return
    if claim.status == ClaimStatus.SUBMITTED:
        claim.status = ClaimStatus.PROCESSING
        claim.processing_stage = "OCR Processing"
        claim.updated_at = utcnow()
        db.commit()
        db.refresh(claim)
    enqueue_claim_processing(claim.id)


def serialize_claim_summary(claim: Claim) -> ClaimSummary:
    return ClaimSummary(
        id=claim.id,
        patient_name=claim.patient_name,
        status=claim.status.value,
        claimed_amount=claim.claimed_amount,
        approved_amount=claim.approved_amount,
        confidence_score=claim.confidence_score,
        created_at=claim.created_at,
    )


def serialize_claim_detail(claim: Claim) -> ClaimDetail:
    summary = serialize_claim_summary(claim)
    return ClaimDetail(
        **summary.model_dump(),
        documents=[
            {
                "id": doc.id,
                "type": doc.document_type.value,
                "filename": doc.filename,
                "preview_url": f"/uploads/{Path(doc.storage_path).name}",
                "ocr_text": doc.ocr_text,
                "ocr_confidence": doc.ocr_confidence,
            }
            for doc in claim.documents
        ],
        extracted_information=claim.extracted_fields.fields if claim.extracted_fields else None,
        policy_evaluation=[
            {
                "rule": log.triggered_rule,
                "decision": log.decision,
                "status": log.decision,
                "explanation": log.explanation,
            }
            for log in claim.decision_logs
        ],
        audit_trail=[
            {
                "label": _audit_label(log.triggered_rule),
                "rule": log.triggered_rule,
                "status": log.decision,
                "explanation": log.explanation,
                "timestamp": log.created_at,
            }
            for log in claim.decision_logs
        ],
        fraud_signals=[
            {
                "code": flag.code,
                "severity": flag.severity,
                "description": flag.description,
            }
            for flag in claim.fraud_flags
        ],
        decision_explanation=claim.decision_logs[0].notes[0] if claim.decision_logs and claim.decision_logs[0].notes else _main_explanation(claim),
    )


def _main_explanation(claim: Claim) -> str | None:
    if not claim.decision_logs:
        return None
    first_failed = next((log for log in claim.decision_logs if log.decision == claim.status.value), claim.decision_logs[0])
    return f"Decision: {claim.status.value}. Triggered Rule: {first_failed.triggered_rule}. Explanation: {first_failed.explanation}"


def _audit_label(rule_code: str) -> str:
    labels = {
        "REQUIRED_DOCUMENTS_PRESENT": "Prescription and medical bill uploaded",
        "REQUIRED_DOCUMENTS_MISSING": "Prescription and medical bill uploaded",
        "REQUIRED_FIELDS_EXTRACTED": "Required claim fields extracted",
        "REQUIRED_FIELDS_MISSING": "Required claim fields extracted",
        "ELIGIBLE_MEMBER": "Eligibility confirmed",
        "WAITING_PERIOD_NOT_SERVED": "Eligibility confirmed",
        "COVERED_OPD_SERVICE": "Covered service confirmed",
        "MIXED_COVERED_AND_EXCLUDED_SERVICES": "Covered service confirmed",
        "EXCLUDED_TREATMENT": "Covered service confirmed",
        "PER_CLAIM_LIMIT_WITHIN_LIMIT": "Within claim limit",
        "PER_CLAIM_LIMIT_EXCEEDED": "Within claim limit",
        "MEDICAL_NECESSITY_PRESENT": "Medical necessity established",
        "MEDICAL_NECESSITY_NOT_ESTABLISHED": "Medical necessity established",
        "NO_FRAUD_SIGNALS": "Fraud validation completed",
        "FRAUD_SIGNALS_FOUND": "Fraud validation completed",
    }
    return labels.get(rule_code, rule_code.replace("_", " ").title())


def processing_stages(claim: Claim) -> list[ProcessingStage]:
    stages = [
        ("Files Uploaded", "Prescription and bill were stored safely."),
        ("OCR Processing", "Raw text and OCR confidence were persisted per document."),
        ("Information Extraction", "Structured Pydantic fields were stored in the database."),
        ("Policy Validation", "Eligibility, coverage and limit rules were evaluated."),
        ("Fraud Detection", "Duplicate, frequency and registration signals were checked."),
        ("Decision Generation", "Final deterministic adjudication decision was generated."),
    ]
    names = [stage[0] for stage in stages]
    completed_until = names.index(claim.processing_stage) if claim.processing_stage in names else len(names) - 1
    return [
        ProcessingStage(
            name=name,
            status="Completed" if index <= completed_until else "Pending",
            detail=detail,
            progress=100 if index <= completed_until else 0,
            started_at=claim.created_at if index <= completed_until else None,
            completed_at=claim.updated_at if index <= completed_until else None,
            confidence_score=claim.confidence_score if name == "Decision Generation" else None,
        )
        for index, (name, detail) in enumerate(stages)
    ]
