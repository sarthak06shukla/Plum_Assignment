import re
from statistics import mean

from backend.app.schemas.decision import ClaimHistoryItem, FraudFinding
from backend.app.schemas.extraction import ExtractedClaimFields


class FraudDetectionModule:
    ACTIVE_HISTORY_STATUSES = {"APPROVED", "PARTIAL", "PARTIAL_APPROVAL"}

    def evaluate(self, fields: ExtractedClaimFields, history: list[ClaimHistoryItem]) -> list[FraudFinding]:
        active_history = [item for item in history if item.status.upper() in self.ACTIVE_HISTORY_STATUSES]
        findings: list[FraudFinding] = []
        findings.extend(self._duplicate_claims(fields, active_history))
        findings.extend(self._same_day_frequency(fields, active_history))
        findings.extend(self._invalid_registration(fields))
        findings.extend(self._suspicious_frequency(active_history))
        findings.extend(self._unusual_amount_pattern(fields, active_history))
        return findings

    def _duplicate_claims(self, fields: ExtractedClaimFields, history: list[ClaimHistoryItem]) -> list[FraudFinding]:
        for item in history:
            same_patient = item.patient_name.lower() == (fields.patient_name or "").lower()
            same_date = item.treatment_date == fields.treatment_date
            same_amount = item.bill_amount == fields.bill_amount
            if same_patient and same_date and same_amount:
                return [
                    FraudFinding(
                        code="DUPLICATE_CLAIM",
                        severity="HIGH",
                        description="A claim with the same patient, treatment date and amount already exists.",
                    )
                ]
        return []

    def _same_day_frequency(self, fields: ExtractedClaimFields, history: list[ClaimHistoryItem]) -> list[FraudFinding]:
        if not fields.treatment_date:
            return []
        same_day = [item for item in history if item.treatment_date == fields.treatment_date]
        if len(same_day) >= 2:
            return [
                FraudFinding(
                    code="EXCESSIVE_SAME_DAY_CLAIMS",
                    severity="MEDIUM",
                    description="Member has multiple OPD claims on the same treatment date.",
                )
            ]
        return []

    def _invalid_registration(self, fields: ExtractedClaimFields) -> list[FraudFinding]:
        registration = fields.doctor_registration_number or ""
        valid_registration = re.match(r"^[A-Z]{2,5}(?:/\d{5}/\d{4}|-\d{5,6})$", registration)
        if registration and not valid_registration:
            return [
                FraudFinding(
                    code="INVALID_DOCTOR_REGISTRATION",
                    severity="MEDIUM",
                    description="Doctor registration number does not match the configured council format.",
                )
            ]
        return []

    def _suspicious_frequency(self, history: list[ClaimHistoryItem]) -> list[FraudFinding]:
        if len(history) >= 4:
            return [
                FraudFinding(
                    code="SUSPICIOUS_CLAIM_FREQUENCY",
                    severity="MEDIUM",
                    description="Member has submitted four or more recent OPD claims.",
                )
            ]
        return []

    def _unusual_amount_pattern(self, fields: ExtractedClaimFields, history: list[ClaimHistoryItem]) -> list[FraudFinding]:
        prior_amounts = [item.bill_amount for item in history if item.bill_amount > 0]
        if len(prior_amounts) < 2:
            return []
        average = mean(prior_amounts)
        if average > 0 and fields.bill_amount > average * 2:
            return [
                FraudFinding(
                    code="UNUSUAL_CLAIM_AMOUNT",
                    severity="LOW",
                    description="Claim amount is more than twice the member's recent OPD average.",
                )
            ]
        return []
