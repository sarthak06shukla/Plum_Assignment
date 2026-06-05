from backend.app.schemas.decision import FraudFinding
from backend.app.services.confidence_engine import ConfidenceEngine


def test_confidence_score_combines_ocr_extraction_documents_and_completeness():
    score = ConfidenceEngine().score(
        ocr_confidence=90,
        extraction_confidence=88,
        required_documents_present=True,
        missing_required_fields=0,
        fraud_findings=[],
    )

    assert score == 90.9


def test_fraud_signals_penalize_confidence():
    score = ConfidenceEngine().score(
        ocr_confidence=90,
        extraction_confidence=88,
        required_documents_present=True,
        missing_required_fields=0,
        fraud_findings=[FraudFinding(code="DUPLICATE_CLAIM", severity="HIGH", description="Duplicate")],
    )

    assert score == 62.9
