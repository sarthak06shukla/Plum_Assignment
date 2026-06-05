from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_admin
from backend.app.db.session import get_db
from backend.app.models.entities import Claim, ClaimStatus, ManualReview, User
from backend.app.services.audit_service import AuditService


router = APIRouter(prefix="/admin", tags=["Admin"])
audit = AuditService()


class OverrideRequest(BaseModel):
    decision: ClaimStatus
    reason: str


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    counts = dict(db.execute(select(Claim.status, func.count()).group_by(Claim.status)).all())
    partial_count = counts.get(ClaimStatus.PARTIAL, 0) + counts.get(ClaimStatus.PARTIAL_APPROVAL, 0)
    return {
        "total_claims": db.scalar(select(func.count()).select_from(Claim)) or 0,
        "approved": counts.get(ClaimStatus.APPROVED, 0),
        "rejected": counts.get(ClaimStatus.REJECTED, 0),
        "partial": partial_count,
        "partial_approval": partial_count,
        "manual_review": counts.get(ClaimStatus.MANUAL_REVIEW, 0),
        "decision_distribution": {
            **{status.value: counts.get(status, 0) for status in ClaimStatus},
            "PARTIAL": partial_count,
        },
    }


@router.get("/claims")
def all_claims(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    claims = db.scalars(select(Claim).order_by(Claim.created_at.desc())).all()
    return [
        {
            "id": claim.id,
            "patient_name": claim.patient_name,
            "status": claim.status.value,
            "claimed_amount": claim.claimed_amount,
            "approved_amount": claim.approved_amount,
            "confidence_score": claim.confidence_score,
            "created_at": claim.created_at,
        }
        for claim in claims
    ]


@router.get("/manual-reviews")
def manual_review_queue(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[dict]:
    reviews = db.scalars(select(ManualReview).order_by(ManualReview.created_at.desc())).all()
    return [
        {
            "review_id": review.id,
            "claim_id": review.claim_id,
            "patient_name": review.claim.patient_name,
            "claimed_amount": review.claim.claimed_amount,
            "status": review.claim.status.value,
            "reason": review.reason,
            "confidence_score": review.claim.confidence_score,
            "fraud_signals": [
                {"code": flag.code, "severity": flag.severity, "description": flag.description}
                for flag in review.claim.fraud_flags
            ],
            "override_decision": review.override_decision,
        }
        for review in reviews
        if review.claim is not None
    ]


@router.post("/manual-reviews/{review_id}/override")
def override_decision(
    review_id: str,
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    review = db.get(ManualReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Manual review not found")

    review.override_decision = payload.decision.value
    review.override_reason = payload.reason
    review.claim.status = payload.decision
    audit.log(
        db,
        actor_id=admin.id,
        entity_type="ManualReview",
        entity_id=review.id,
        action="OVERRIDE_DECISION",
        payload={"decision": payload.decision.value, "reason": payload.reason},
    )
    db.commit()
    return {"status": "saved", "claim_id": review.claim_id, "decision": payload.decision.value}
