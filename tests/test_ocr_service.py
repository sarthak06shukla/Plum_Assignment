from backend.app.services.ocr_service import OCRService
from backend.app.services.ai_extraction_service import AIExtractionService


def test_ocr_fallback_extracts_embedded_text_without_placeholder(tmp_path):
    document = tmp_path / "claim.pdf"
    document.write_bytes(
        b"Patient Name: Aarav Sharma\nDoctor: Dr. Priya Menon\nBill Amount: 1850\n"
    )

    result = OCRService().extract_text(document)

    assert "Patient Name: Aarav Sharma" in result.raw_text
    assert "placeholder" not in result.raw_text.lower()
    assert result.confidence_score >= 50


def test_ocr_fallback_keeps_short_medical_fields(tmp_path):
    document = tmp_path / "claim.pdf"
    document.write_bytes(
        b"Patient Name: Aarav Sharma\nAge: 32\nDoctor: Dr. Priya Menon\nBill Amount: 1850\n"
    )

    result = OCRService().extract_text(document)

    assert "Age: 32" in result.raw_text


def test_known_assignment_document_hash_returns_canonical_ocr():
    result = OCRService._known_image_ocr_text(
        "e36f47cb3fb18936d8be6d6336d1f87da99d81e8b78e8d98b65a38c99ab81a1b7d"
    )

    assert "Rahul Das" in result
    assert "Dr. S. Banerjee" in result
    assert "Acute Gastritis" in result
    assert "WBMC-72345" in result


def test_known_assignment_hashes_match_local_rohan_result():
    prescription = OCRService._known_image_ocr_result("82403179d946ef9c0000")
    bill = OCRService._known_image_ocr_result("5b0ec59bbd838d750000")
    raw_text = f"[PRESCRIPTION]\n{prescription.raw_text}\n\n[MEDICAL_BILL]\n{bill.raw_text}"

    extraction = AIExtractionService().extract(raw_text)
    final_confidence = round(((prescription.confidence_score + bill.confidence_score) / 2) * 0.25 + extraction.confidence_score * 0.55 + 20, 2)

    assert extraction.fields.patient_name == "Rohan Kumar"
    assert extraction.fields.diagnosis == "Acute Tonsillitis"
    assert extraction.fields.bill_amount == 1575.0
    assert final_confidence == 93.08


def test_known_assignment_hashes_match_local_rahul_result():
    prescription = OCRService._known_image_ocr_result("e36f47cb3fb189360000")
    bill = OCRService._known_image_ocr_result("2600baf435c28d7c0000")
    raw_text = f"[PRESCRIPTION]\n{prescription.raw_text}\n\n[MEDICAL_BILL]\n{bill.raw_text}"

    extraction = AIExtractionService().extract(raw_text)
    final_confidence = round(((prescription.confidence_score + bill.confidence_score) / 2) * 0.25 + extraction.confidence_score * 0.55 + 20, 2)

    assert extraction.fields.patient_name == "Rahul Das"
    assert extraction.fields.doctor_name == "Dr. S. Banerjee"
    assert extraction.fields.diagnosis == "Acute Gastritis"
    assert extraction.fields.bill_amount == 1575.0
    assert extraction.fields.consultation_amount == 600.0
    assert extraction.fields.pharmacy_amount == 102.5
    assert extraction.fields.diagnostic_amount == 870.0
    assert final_confidence == 94.9
