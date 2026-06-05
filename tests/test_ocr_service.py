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
