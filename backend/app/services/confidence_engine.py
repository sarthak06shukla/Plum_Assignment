from backend.app.schemas.decision import FraudFinding


class ConfidenceEngine:
    def score(
        self,
        *,
        ocr_confidence: float,
        extraction_confidence: float,
        required_documents_present: bool,
        missing_required_fields: int,
        fraud_findings: list[FraudFinding],
    ) -> float:
        document_score = 100 if required_documents_present else 40
        extraction_completeness = max(0, extraction_confidence - missing_required_fields * 4)
        fraud_penalty = sum(self._fraud_penalty(finding.severity) for finding in fraud_findings)

        # Clean claims should not be punished too hard for imperfect OCR when
        # structured extraction is complete and both required documents exist.
        score = (
            ocr_confidence * 0.25
            + extraction_completeness * 0.55
            + document_score * 0.2
            - fraud_penalty
        )
        return round(max(0, min(score, 100)), 2)

    @staticmethod
    def _fraud_penalty(severity: str) -> float:
        penalties = {"LOW": 10, "MEDIUM": 22, "HIGH": 28}
        return penalties.get(severity.upper(), 18)
