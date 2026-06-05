from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Claim,
    ClaimStatus,
    DecisionLog,
    Document,
    ExtractedFields,
    FraudFlag,
    ManualReview,
    utcnow,
)
from backend.app.schemas.decision import ClaimAdjudicationInput, ClaimHistoryItem, Decision, PolicyContext
from backend.app.services.ai_extraction_service import AIExtractionService
from backend.app.services.ocr_service import OCRService
from backend.app.services.rule_engine import RuleEngine


class ClaimProcessor:
    def __init__(self) -> None:
        self.ocr = OCRService()
        self.extractor = AIExtractionService()
        self.rules = RuleEngine()

    def process(self, db: Session, claim: Claim) -> Claim:
        claim.status = ClaimStatus.PROCESSING
        claim.processing_stage = "OCR Processing"
        db.flush()

        ocr_scores: list[float] = []
        raw_text_parts: list[str] = []
        for document in claim.documents:
            result = self.ocr.extract_text(path=document_path(document))
            document.ocr_text = result.raw_text
            document.ocr_confidence = result.confidence_score
            ocr_scores.append(result.confidence_score)
            raw_text_parts.append(f"[{document.document_type.value}]\n{result.raw_text}")

        claim.processing_stage = "Information Extraction"
        extraction = self.extractor.extract("\n\n".join(raw_text_parts))
        claim.patient_name = extraction.fields.patient_name
        claim.claimed_amount = extraction.fields.bill_amount

        existing = claim.extracted_fields or ExtractedFields(
            claim_id=claim.id,
            fields=extraction.fields.model_dump(mode="json"),
            extraction_confidence=extraction.confidence_score,
        )
        existing.fields = extraction.fields.model_dump(mode="json")
        existing.extraction_confidence = extraction.confidence_score
        db.add(existing)

        claim.processing_stage = "Policy Validation"
        annual_claimed = self._annual_claimed_amount(db, claim.user_id, exclude_claim_id=claim.id)
        history = self._claim_history(db, claim.user_id, exclude_claim_id=claim.id)
        policy_context = PolicyContext(
            member_id=claim.user_id,
            policy_start_date=date(2025, 1, 1),
            annual_claimed_amount=annual_claimed,
            provider_network_status="IN_NETWORK",
        )
        adjudication_input = ClaimAdjudicationInput(
            extracted_fields=extraction.fields,
            document_types=[document.document_type.value for document in claim.documents],
            ocr_confidence=round(sum(ocr_scores) / len(ocr_scores), 2) if ocr_scores else 0,
            extraction_confidence=extraction.confidence_score,
            policy_context=policy_context,
            claim_history=history,
        )

        claim.processing_stage = "Decision Generation"
        decision = self.rules.evaluate(adjudication_input)
        claim.status = ClaimStatus(decision.decision.value)
        claim.approved_amount = decision.approved_amount
        claim.confidence_score = decision.confidence_score
        claim.policy_snapshot = decision.policy_snapshot
        claim.updated_at = utcnow()

        self._replace_decision_artifacts(db, claim, decision)
        return claim

    def _replace_decision_artifacts(self, db: Session, claim: Claim, decision) -> None:
        for row in list(claim.decision_logs) + list(claim.fraud_flags) + list(claim.manual_reviews):
            db.delete(row)
        db.flush()

        for rule in decision.triggered_rules:
            rule_result = "ADJUSTED" if rule.amount_adjustment is not None else "PASSED" if rule.passed else "FAILED"
            db.add(
                DecisionLog(
                    claim_id=claim.id,
                    decision=rule_result,
                    triggered_rule=rule.code,
                    explanation=rule.explanation,
                    notes=[decision.explanation, *decision.notes],
                )
            )

        for finding in decision.fraud_findings:
            db.add(
                FraudFlag(
                    claim_id=claim.id,
                    code=finding.code,
                    severity=finding.severity,
                    description=finding.description,
                )
            )

        if decision.decision == Decision.MANUAL_REVIEW:
            reason = "; ".join(decision.notes) or "Claim requires reviewer confirmation before payout."
            db.add(ManualReview(claim_id=claim.id, reason=reason))

    def _annual_claimed_amount(self, db: Session, user_id: str, exclude_claim_id: str) -> float:
        total = db.scalar(
            select(func.coalesce(func.sum(Claim.approved_amount), 0.0)).where(
                Claim.user_id == user_id,
                Claim.id != exclude_claim_id,
                Claim.status.in_([ClaimStatus.APPROVED, ClaimStatus.PARTIAL, ClaimStatus.PARTIAL_APPROVAL]),
            )
        )
        return float(total or 0)

    def _claim_history(self, db: Session, user_id: str, exclude_claim_id: str) -> list[ClaimHistoryItem]:
        rows = db.execute(
            select(Claim, ExtractedFields)
            .outerjoin(ExtractedFields, ExtractedFields.claim_id == Claim.id)
            .where(Claim.user_id == user_id, Claim.id != exclude_claim_id)
            .order_by(Claim.created_at.desc())
            .limit(20)
        ).all()
        history: list[ClaimHistoryItem] = []
        for claim, extracted in rows:
            fields = extracted.fields if extracted else {}
            history.append(
                ClaimHistoryItem(
                    claim_id=claim.id,
                    patient_name=fields.get("patient_name") or claim.patient_name or "",
                    treatment_date=date.fromisoformat(fields["treatment_date"]) if fields.get("treatment_date") else None,
                    bill_amount=float(fields.get("bill_amount") or claim.claimed_amount or 0),
                    doctor_registration_number=fields.get("doctor_registration_number"),
                    status=claim.status.value,
                    created_at=claim.created_at.date(),
                )
            )
        return history


def document_path(document: Document):
    from pathlib import Path

    return Path(document.storage_path)
