from datetime import date

from backend.app.schemas.decision import ClaimAdjudicationInput, ClaimHistoryItem, Decision, PolicyContext
from backend.app.schemas.extraction import ExtractedClaimFields
from backend.app.services.rule_engine import RuleEngine


def make_input(
    *,
    fields: ExtractedClaimFields | None = None,
    documents: list[str] | None = None,
    ocr_confidence: float = 90,
    extraction_confidence: float = 90,
    history: list[ClaimHistoryItem] | None = None,
    policy_start_date: date = date(2025, 1, 1),
    annual_claimed_amount: float = 0,
) -> ClaimAdjudicationInput:
    return ClaimAdjudicationInput(
        extracted_fields=fields or valid_fields(),
        document_types=documents or ["PRESCRIPTION", "MEDICAL_BILL"],
        ocr_confidence=ocr_confidence,
        extraction_confidence=extraction_confidence,
        policy_context=PolicyContext(
            member_id="MBR-1",
            policy_start_date=policy_start_date,
            annual_claimed_amount=annual_claimed_amount,
        ),
        claim_history=history or [],
    )


def valid_fields(**overrides) -> ExtractedClaimFields:
    data = {
        "patient_name": "Aarav Sharma",
        "patient_age": 32,
        "doctor_name": "Dr. Priya Menon",
        "doctor_registration_number": "MH/12345/2019",
        "diagnosis": "Viral fever",
        "medicines": ["Paracetamol"],
        "procedures": [],
        "tests": [],
        "treatment_date": date(2026, 5, 14),
        "hospital_name": "CityCare Clinic",
        "bill_amount": 1850,
        "consultation_amount": 800,
        "pharmacy_amount": 1050,
        "diagnostic_amount": 0,
    }
    data.update(overrides)
    return ExtractedClaimFields(**data)


def rule_codes(result):
    return [rule.code for rule in result.triggered_rules]


def test_approves_claim_when_all_policy_rules_pass():
    result = RuleEngine().evaluate(make_input())

    assert result.decision == Decision.APPROVED
    assert result.approved_amount == 1850
    assert "ELIGIBLE_MEMBER" in rule_codes(result)
    assert "NO_FRAUD_SIGNALS" in rule_codes(result)


def test_rejects_when_per_claim_limit_is_exceeded():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(bill_amount=7500, pharmacy_amount=2500, diagnostic_amount=2500)))

    assert result.decision == Decision.REJECTED
    assert result.approved_amount == 0
    assert "PER_CLAIM_LIMIT_EXCEEDED" in rule_codes(result)


def test_missing_prescription_rejects_claim():
    result = RuleEngine().evaluate(make_input(documents=["MEDICAL_BILL"]))

    assert result.decision == Decision.REJECTED
    assert result.approved_amount == 0
    assert "REQUIRED_DOCUMENTS_MISSING" in rule_codes(result)


def test_excluded_treatment_rejects_claim():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(diagnosis="Cosmetic dermatology procedure")))

    assert result.decision == Decision.REJECTED
    assert "EXCLUDED_TREATMENT" in rule_codes(result)


def test_waiting_period_rejects_claim():
    result = RuleEngine().evaluate(make_input(policy_start_date=date(2026, 5, 1)))

    assert result.decision == Decision.REJECTED
    assert "WAITING_PERIOD_NOT_SERVED" in rule_codes(result)


def test_missing_required_treatment_date_routes_to_manual_review():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(treatment_date=None)))

    assert result.decision == Decision.MANUAL_REVIEW
    assert "REQUIRED_FIELDS_MISSING" in rule_codes(result)


def test_blurry_document_routes_to_manual_review_when_confidence_is_low():
    result = RuleEngine().evaluate(make_input(ocr_confidence=35, extraction_confidence=60))

    assert result.decision == Decision.MANUAL_REVIEW
    assert result.confidence_score < 70
    assert any("Confidence below 70" in note for note in result.notes)


def test_duplicate_claim_routes_to_manual_review_not_rejection():
    fields = valid_fields()
    duplicate = ClaimHistoryItem(
        claim_id="CLM-OLD",
        patient_name=fields.patient_name or "",
        treatment_date=fields.treatment_date,
        bill_amount=fields.bill_amount,
        doctor_registration_number=fields.doctor_registration_number,
        status="APPROVED",
    )

    result = RuleEngine().evaluate(make_input(fields=fields, history=[duplicate]))

    assert result.decision == Decision.MANUAL_REVIEW
    assert result.approved_amount == fields.bill_amount
    assert "FRAUD_SIGNALS_FOUND" in rule_codes(result)
    assert result.fraud_findings[0].code == "DUPLICATE_CLAIM"


def test_invalid_registration_routes_to_manual_review_not_rejection():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(doctor_registration_number="BAD-REG-77")))

    assert result.decision == Decision.MANUAL_REVIEW
    assert result.fraud_findings[0].code == "INVALID_DOCTOR_REGISTRATION"


def test_annual_limit_exhausted_rejects_claim():
    result = RuleEngine().evaluate(make_input(annual_claimed_amount=25000))
    assert result.decision == Decision.REJECTED
    assert "ANNUAL_LIMIT_EXHAUSTED" in rule_codes(result)


def test_annual_limit_partial_caps_amount():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(bill_amount=3000, pharmacy_amount=1500, consultation_amount=800, diagnostic_amount=700), annual_claimed_amount=23000))
    assert result.approved_amount <= 2000


def test_category_sub_limit_adjusts_pharmacy():
    result = RuleEngine().evaluate(make_input(fields=valid_fields(bill_amount=4500, pharmacy_amount=4000, consultation_amount=500)))
    assert result.decision == Decision.PARTIAL
    codes = rule_codes(result)
    assert "PHARMACY_SUB_LIMIT_EXCEEDED" in codes


def test_root_canal_with_whitening_is_partial():
    result = RuleEngine().evaluate(
        make_input(
            fields=valid_fields(
                diagnosis="Root canal with teeth whitening",
                procedures=["Root canal", "Teeth whitening"],
                bill_amount=4200,
                consultation_amount=500,
                pharmacy_amount=700,
                diagnostic_amount=0,
            )
        )
    )

    assert result.decision == Decision.PARTIAL
    assert "MIXED_COVERED_AND_EXCLUDED_SERVICES" in rule_codes(result)
