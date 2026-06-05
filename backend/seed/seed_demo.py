from datetime import date

from sqlalchemy import select

from backend.app.core.security import hash_password
from backend.app.db.session import Base, SessionLocal, engine
from backend.app.models.entities import (
    Claim,
    ClaimStatus,
    DecisionLog,
    ExtractedFields,
    FraudFlag,
    ManualReview,
    User,
    UserRole,
)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = get_or_create_user(db, "admin@plum.demo", "Ops Admin", "admin123", UserRole.ADMIN)
        user = get_or_create_user(db, "member@plum.demo", "Demo Member", "member123", UserRole.USER)
        if db.scalar(select(Claim).where(Claim.id == "CLM-1001")):
            return

        examples = [
            ("CLM-1001", "Aarav Sharma", ClaimStatus.APPROVED, 1850, 1850, 91, "Viral fever", "MH/12345/2019"),
            ("CLM-1002", "Meera Iyer", ClaimStatus.PARTIAL, 4200, 2730, 89, "Root canal with teeth whitening", "KA/55321/2018"),
            ("CLM-1003", "Rohan Verma", ClaimStatus.MANUAL_REVIEW, 4200, 4200, 64, "Upper respiratory infection", "BAD-REG-77"),
            ("CLM-1004", "Nisha Rao", ClaimStatus.REJECTED, 7500, 0, 83, "Migraine consultation", "DL/77890/2020"),
        ]
        decision_rules = {
            "CLM-1001": ("PASSED", "ELIGIBLE_MEMBER", "All policy rules passed. Claim amount Rs 1,850 is within limits."),
            "CLM-1002": ("ADJUSTED", "MIXED_COVERED_AND_EXCLUDED_SERVICES", "Root canal is covered, while teeth whitening is excluded. Payable amount was reduced."),
            "CLM-1003": ("FAILED", "FRAUD_SIGNALS_FOUND", "Invalid doctor registration and low confidence require manual review."),
            "CLM-1004": ("FAILED", "PER_CLAIM_LIMIT_EXCEEDED", "Claim amount Rs 7,500 exceeds per-claim limit of Rs 5,000."),
        }
        for claim_id, patient, status, claimed, approved, confidence, diagnosis, registration in examples:
            claim = Claim(
                id=claim_id,
                user_id=user.id,
                patient_name=patient,
                status=status,
                claimed_amount=claimed,
                approved_amount=approved,
                confidence_score=confidence,
                processing_stage="Decision Generation",
            )
            db.add(claim)
            db.add(
                ExtractedFields(
                    claim_id=claim_id,
                    fields={
                        "patient_name": patient,
                        "patient_age": 34,
                        "doctor_name": "Dr. Priya Menon",
                        "doctor_registration_number": registration,
                        "diagnosis": diagnosis,
                        "medicines": ["Paracetamol"],
                        "procedures": ["Root canal", "Teeth whitening"] if status == ClaimStatus.PARTIAL else [],
                        "tests": ["CBC"] if status == ClaimStatus.PARTIAL else [],
                        "treatment_date": date(2026, 5, 14).isoformat(),
                        "hospital_name": "CityCare Clinic",
                        "bill_amount": claimed,
                        "consultation_amount": 800,
                        "pharmacy_amount": min(1200, claimed),
                        "diagnostic_amount": max(0, claimed - 2000),
                    },
                    extraction_confidence=confidence,
                )
            )
            rule_result, triggered, explanation = decision_rules[claim_id]
            db.add(
                DecisionLog(
                    claim_id=claim_id,
                    decision=rule_result,
                    triggered_rule=triggered,
                    explanation=explanation,
                    notes=[
                        f"Decision: {status.value}\nReason: {explanation}\nImpact: Demo claim illustrates this adjudication outcome.\nRecommended Action: Review supporting documents before payout."
                    ],
                )
            )

        db.add(
            FraudFlag(
                claim_id="CLM-1003",
                code="INVALID_DOCTOR_REGISTRATION",
                severity="MEDIUM",
                description="Doctor registration number does not match the configured council format XX/XXXXX/XXXX.",
            )
        )
        db.add(
            ManualReview(
                claim_id="CLM-1003",
                reason="Low confidence score (64%) and invalid doctor registration format detected.",
            )
        )
        db.commit()
        print(f"Seeded demo users: {admin.email}, {user.email}")
    finally:
        db.close()


def get_or_create_user(db, email: str, name: str, password: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, name=name, role=role, hashed_password=hash_password(password))
    db.add(user)
    db.flush()
    return user


if __name__ == "__main__":
    seed()
