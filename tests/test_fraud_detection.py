from datetime import date

from backend.app.schemas.decision import ClaimHistoryItem
from backend.app.schemas.extraction import ExtractedClaimFields
from backend.app.services.fraud_detection import FraudDetectionModule


def fields(**overrides):
    data = {
        "patient_name": "Rohan Verma",
        "doctor_registration_number": "BAD-REG-77",
        "diagnosis": "Upper respiratory infection",
        "medicines": ["Azithromycin"],
        "treatment_date": date(2026, 5, 19),
        "hospital_name": "Metro Diagnostic Center",
        "bill_amount": 4200,
    }
    data.update(overrides)
    return ExtractedClaimFields(**data)


def test_invalid_doctor_registration_is_flagged():
    findings = FraudDetectionModule().evaluate(fields(), [])

    assert any(finding.code == "INVALID_DOCTOR_REGISTRATION" for finding in findings)


def test_hyphenated_medical_council_registration_is_allowed():
    findings = FraudDetectionModule().evaluate(fields(doctor_registration_number="WBMC-72345"), [])

    assert not any(finding.code == "INVALID_DOCTOR_REGISTRATION" for finding in findings)


def test_excessive_same_day_claims_are_flagged():
    history = [
        ClaimHistoryItem(claim_id="1", patient_name="A", treatment_date=date(2026, 5, 19), bill_amount=500, status="APPROVED"),
        ClaimHistoryItem(claim_id="2", patient_name="B", treatment_date=date(2026, 5, 19), bill_amount=700, status="APPROVED"),
    ]

    findings = FraudDetectionModule().evaluate(fields(doctor_registration_number="MH/12345/2019"), history)

    assert any(finding.code == "EXCESSIVE_SAME_DAY_CLAIMS" for finding in findings)


def test_duplicate_claim_is_flagged():
    f = fields(doctor_registration_number="MH/12345/2019")
    history = [
        ClaimHistoryItem(
            claim_id="OLD",
            patient_name=f.patient_name or "",
            treatment_date=f.treatment_date,
            bill_amount=f.bill_amount,
            doctor_registration_number=f.doctor_registration_number,
            status="APPROVED",
        )
    ]
    findings = FraudDetectionModule().evaluate(f, history)
    assert any(finding.code == "DUPLICATE_CLAIM" for finding in findings)


def test_suspicious_frequency_is_flagged():
    f = fields(doctor_registration_number="MH/12345/2019")
    history = [
        ClaimHistoryItem(claim_id=str(i), patient_name="A", treatment_date=None, bill_amount=500, status="APPROVED")
        for i in range(5)
    ]
    findings = FraudDetectionModule().evaluate(f, history)
    assert any(finding.code == "SUSPICIOUS_CLAIM_FREQUENCY" for finding in findings)


def test_suspicious_frequency_ignores_rejected_and_manual_retry_history():
    f = fields(doctor_registration_number="MH/12345/2019")
    history = [
        ClaimHistoryItem(claim_id="manual", patient_name="A", treatment_date=None, bill_amount=500, status="MANUAL_REVIEW"),
        ClaimHistoryItem(claim_id="rejected", patient_name="B", treatment_date=None, bill_amount=500, status="REJECTED"),
        ClaimHistoryItem(claim_id="processing", patient_name="C", treatment_date=None, bill_amount=500, status="PROCESSING"),
        ClaimHistoryItem(claim_id="submitted", patient_name="D", treatment_date=None, bill_amount=500, status="SUBMITTED"),
    ]
    findings = FraudDetectionModule().evaluate(f, history)
    assert not any(finding.code == "SUSPICIOUS_CLAIM_FREQUENCY" for finding in findings)


def test_unusual_amount_is_flagged():
    f = fields(doctor_registration_number="MH/12345/2019", bill_amount=10000)
    history = [
        ClaimHistoryItem(claim_id="1", patient_name="A", treatment_date=None, bill_amount=500, status="APPROVED"),
        ClaimHistoryItem(claim_id="2", patient_name="A", treatment_date=None, bill_amount=600, status="APPROVED"),
    ]
    findings = FraudDetectionModule().evaluate(f, history)
    assert any(finding.code == "UNUSUAL_CLAIM_AMOUNT" for finding in findings)
