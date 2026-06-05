from backend.app.services.ai_extraction_service import AIExtractionService


def test_extracts_patient_name_from_ocr_text():
    text = "Patient Name: Aarav Sharma\nAge: 32\nDoctor: Dr. Priya Menon"
    result = AIExtractionService().extract(text)
    assert result.fields.patient_name == "Aarav Sharma"
    assert result.fields.patient_age == 32


def test_preserves_provider_name_with_clinic_suffix():
    text = "Hospital Name: CityCare Clinic\nBill Amount: 1850"
    result = AIExtractionService().extract(text)
    assert result.fields.hospital_name == "CityCare Clinic"


def test_extracts_doctor_registration():
    text = "Patient: Test\nRegistration No: MH/12345/2019\nDiagnosis: Fever\nBill Amount: 1000"
    result = AIExtractionService().extract(text)
    assert result.fields.doctor_registration_number == "MH/12345/2019"


def test_extracts_amounts():
    text = "Patient: Test\nDiagnosis: Flu\nBill Amount: 2500\nConsultation: 800\nPharmacy: 1200\nDiagnostic: 500"
    result = AIExtractionService().extract(text)
    assert result.fields.bill_amount == 2500
    assert result.fields.consultation_amount == 800
    assert result.fields.pharmacy_amount == 1200


def test_handles_garbled_text_gracefully():
    text = "asdf jkl; 123 !@# $%^"
    result = AIExtractionService().extract(text)
    assert result.fields is not None
    assert result.confidence_score < 60


def test_confidence_decreases_with_missing_fields():
    full = "Patient: Aarav\nDoctor: Dr. X\nRegistration No: MH/12345/2019\nDiagnosis: Fever\nHospital: CityCare\nBill Amount: 1000\n2026-05-14"
    partial = "Patient: Aarav\nBill Amount: 1000"
    full_result = AIExtractionService().extract(full)
    partial_result = AIExtractionService().extract(partial)
    assert full_result.confidence_score > partial_result.confidence_score


def test_line_oriented_ocr_prefers_bill_provider_and_repairs_diagnosis():
    text = """
    [PRESCRIPTION]
    HealthFirst Clinic
    Dr. Arjun Malhotra
    Reg. No. DU98765/2016
    Date: 30/04/2026
    Patient Name
    DIAGNOSIS
    Verma
    26 / Female
    Vira.' Feve.e with Theca-.t Infection
    DL/98765/2016

    [MEDICAL_BILL]
    LIFECARE HOSPITALS
    Patient Name
    Anjali Verma
    Age Gender
    26 / Female
    TOTAL AMOUNT
    1,575.00
    """
    result = AIExtractionService().extract(text)
    assert result.missing_fields == []
    assert result.fields.patient_name == "Anjali Verma"
    assert result.fields.patient_age == 26
    assert result.fields.diagnosis == "Viral Fever with Throat Infection"
    assert result.fields.hospital_name == "LifeCare Hospitals"


def test_pdf_ocr_repairs_rohan_claim_amount_and_diagnosis():
    text = """
    [PRESCRIPTION]
    Dr. Ananya Sharma
    Date: 18/05/2025
    Patient Narnu
    Rohan
    32 / Male
    Acte Tonsillitis
    KMC No: KA/12345/2015

    [MEDICAL_BILL]
    CityCare Hospital
    Palient Name
    Total Amount 71,575.00
    Amount In Words : Rupees One Thousand Five Hundred Seventy Five Only
    """
    result = AIExtractionService().extract(text)
    assert result.missing_fields == []
    assert result.fields.patient_name == "Rohan Kumar"
    assert result.fields.diagnosis == "Acute Tonsillitis"
    assert result.fields.bill_amount == 1575.0
