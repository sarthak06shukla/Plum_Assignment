from sqlalchemy import delete

from backend.app.db.session import Base, SessionLocal, engine
from backend.app.models.entities import AuditLog, Claim, DecisionLog, Document, ExtractedFields, FraudFlag, ManualReview


DEMO_CLAIM_IDS = ["CLM-1001", "CLM-1002", "CLM-1003", "CLM-1004"]


def clear_demo_claims() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(delete(ManualReview).where(ManualReview.claim_id.in_(DEMO_CLAIM_IDS)))
        db.execute(delete(FraudFlag).where(FraudFlag.claim_id.in_(DEMO_CLAIM_IDS)))
        db.execute(delete(DecisionLog).where(DecisionLog.claim_id.in_(DEMO_CLAIM_IDS)))
        db.execute(delete(ExtractedFields).where(ExtractedFields.claim_id.in_(DEMO_CLAIM_IDS)))
        db.execute(delete(Document).where(Document.claim_id.in_(DEMO_CLAIM_IDS)))
        db.execute(delete(AuditLog).where(AuditLog.entity_id.in_(DEMO_CLAIM_IDS)))
        result = db.execute(delete(Claim).where(Claim.id.in_(DEMO_CLAIM_IDS)))
        db.commit()
        print(f"Removed {result.rowcount or 0} seeded demo claims.")
    finally:
        db.close()


if __name__ == "__main__":
    clear_demo_claims()
