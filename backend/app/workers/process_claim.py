import logging
import sys

from backend.app.db.session import SessionLocal
from backend.app.models.entities import Claim, ClaimStatus, DecisionLog, ManualReview, utcnow
from backend.app.services.claim_processor import ClaimProcessor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_claim(claim_id: str) -> int:
    db = SessionLocal()
    try:
        claim = db.get(Claim, claim_id)
        if not claim:
            logger.warning("Claim not found: %s", claim_id)
            return 1
        ClaimProcessor().process(db, claim)
        db.commit()
        logger.info("Claim processed: %s status=%s confidence=%s", claim.id, claim.status.value, claim.confidence_score)
        return 0
    except Exception as exc:
        db.rollback()
        logger.exception("Claim processing failed: %s", claim_id)
        _mark_failed(db, claim_id, str(exc))
        return 1
    finally:
        db.close()


def _mark_failed(db, claim_id: str, error: str) -> None:
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
            notes=[f"OCR or extraction failed in the worker process: {error[:300]}"],
        )
    )
    db.add(ManualReview(claim_id=claim.id, reason="Automated claim processing failed after upload."))
    db.commit()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m backend.app.workers.process_claim <claim_id>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(process_claim(sys.argv[1]))
