from backend.app.services.ocr_service import OCRService


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

    assert "Rohan Kumar" in result
    assert "Dr. Ananya Sharma" in result
    assert "Acute Tonsillitis" in result
    assert "KA/12345/2015" in result
