from datetime import date

from backend.app.schemas.decision import (
    ClaimAdjudicationInput,
    Decision,
    RuleCategory,
    RuleDecision,
    TriggeredRule,
)
from backend.app.services.confidence_engine import ConfidenceEngine
from backend.app.services.explanation_service import DecisionExplanationService
from backend.app.services.fraud_detection import FraudDetectionModule
from backend.app.services.policy_engine import PolicyEngine


class RuleEngine:
    def __init__(self) -> None:
        self.policy = PolicyEngine()
        self.fraud = FraudDetectionModule()
        self.confidence = ConfidenceEngine()
        self.explainer = DecisionExplanationService()

    def evaluate(self, claim: ClaimAdjudicationInput) -> RuleDecision:
        rules: list[TriggeredRule] = []
        notes: list[str] = []
        fields = claim.extracted_fields
        approved_amount = float(fields.bill_amount)

        rules.append(self._eligibility_rule(claim.policy_context.policy_start_date, fields.treatment_date))
        rules.append(self._required_documents_rule(claim.document_types))
        missing_required_fields = self._missing_required_fields_count(claim)
        rules.append(self._field_completeness_rule(missing_required_fields))
        coverage_rule = self._coverage_rule(fields)
        rules.append(coverage_rule)
        rules.append(self._network_rule(fields.hospital_name or "", claim.policy_context.provider_network_status))
        limit_rules, approved_amount = self._limit_rules(fields, claim.policy_context.annual_claimed_amount)
        rules.extend(limit_rules)
        if coverage_rule.amount_adjustment is not None:
            approved_amount = max(0, approved_amount + coverage_rule.amount_adjustment)

        necessity = self._medical_necessity_rule(fields.diagnosis, fields.medicines, fields.procedures, fields.tests)
        rules.append(necessity)

        fraud_findings = self.fraud.evaluate(fields, claim.claim_history)
        if fraud_findings:
            rules.append(
                TriggeredRule(
                    code="FRAUD_SIGNALS_FOUND",
                    category=RuleCategory.FRAUD_CHECKS,
                    passed=False,
                    explanation="Fraud signals were detected and the claim requires manual review.",
                )
            )
            notes.extend(flag.description for flag in fraud_findings)
        else:
            rules.append(
                TriggeredRule(
                    code="NO_FRAUD_SIGNALS",
                    category=RuleCategory.FRAUD_CHECKS,
                    passed=True,
                    explanation="No configured fraud signal was detected.",
                )
            )

        required_documents_present = self._has_required_documents(claim.document_types)
        confidence_score = self.confidence.score(
            ocr_confidence=claim.ocr_confidence,
            extraction_confidence=claim.extraction_confidence,
            required_documents_present=required_documents_present,
            missing_required_fields=missing_required_fields,
            fraud_findings=fraud_findings,
        )

        decision = self._decision_from_rules(rules, approved_amount, confidence_score, fraud_findings, missing_required_fields)
        if confidence_score < 70 and decision != Decision.REJECTED:
            notes.append("Confidence below 70 requires human review before payout.")
        if missing_required_fields and decision == Decision.MANUAL_REVIEW:
            notes.append("Required extracted fields are missing and need reviewer verification.")

        result = RuleDecision(
            decision=decision,
            approved_amount=0 if decision == Decision.REJECTED else round(approved_amount, 2),
            triggered_rules=rules,
            notes=notes,
            fraud_findings=fraud_findings,
            confidence_score=confidence_score,
            policy_snapshot=self.policy.snapshot(),
        )
        result.explanation = self.explainer.explain(result)
        return result

    def _eligibility_rule(self, policy_start: date, treatment_date: date | None) -> TriggeredRule:
        if not treatment_date:
            return TriggeredRule(
                code="TREATMENT_DATE_MISSING",
                category=RuleCategory.ELIGIBILITY,
                passed=False,
                explanation="Treatment date is missing, so eligibility cannot be verified.",
            )

        elapsed = (treatment_date - policy_start).days
        if elapsed < self.policy.waiting_period_days():
            return TriggeredRule(
                code="WAITING_PERIOD_NOT_SERVED",
                category=RuleCategory.ELIGIBILITY,
                passed=False,
                explanation=(
                    f"Treatment date is {elapsed} days after policy start; "
                    f"configured waiting period is {self.policy.waiting_period_days()} days."
                ),
            )
        return TriggeredRule(
            code="ELIGIBLE_MEMBER",
            category=RuleCategory.ELIGIBILITY,
            passed=True,
            explanation="Member is eligible for OPD adjudication on the treatment date.",
        )

    def _required_documents_rule(self, document_types: list[str]) -> TriggeredRule:
        if self._has_required_documents(document_types):
            return TriggeredRule(
                code="REQUIRED_DOCUMENTS_PRESENT",
                category=RuleCategory.DOCUMENT_VALIDATION,
                passed=True,
                explanation="Prescription and medical bill were uploaded.",
            )
        return TriggeredRule(
            code="REQUIRED_DOCUMENTS_MISSING",
            category=RuleCategory.DOCUMENT_VALIDATION,
            passed=False,
            explanation="Prescription and medical bill are mandatory for OPD claims.",
        )

    def _field_completeness_rule(self, missing_required_fields: int) -> TriggeredRule:
        if missing_required_fields == 0:
            return TriggeredRule(
                code="REQUIRED_FIELDS_EXTRACTED",
                category=RuleCategory.DOCUMENT_VALIDATION,
                passed=True,
                explanation="Required patient, provider, treatment and amount fields were extracted.",
            )
        return TriggeredRule(
            code="REQUIRED_FIELDS_MISSING",
            category=RuleCategory.DOCUMENT_VALIDATION,
            passed=False,
            explanation=f"{missing_required_fields} required extracted field(s) are missing.",
        )

    def _coverage_rule(self, fields) -> TriggeredRule:
        service_text = " ".join(
            [
                fields.diagnosis or "",
                " ".join(fields.procedures),
                " ".join(fields.tests),
                " ".join(fields.medicines),
            ]
        ).lower()
        exclusions = [item for item in self.policy.exclusions() if item in service_text]
        covered = [item for item in self.policy.covered_services() if item in service_text]
        if exclusions and covered:
            reduction = fields.bill_amount * (self.policy.mixed_exclusion_reduction_percent() / 100)
            return TriggeredRule(
                code="MIXED_COVERED_AND_EXCLUDED_SERVICES",
                category=RuleCategory.COVERAGE_VALIDATION,
                passed=True,
                explanation=(
                    f"Claim includes covered service(s) {', '.join(covered)} and excluded service(s) "
                    f"{', '.join(exclusions)}; excluded portion is not payable."
                ),
                amount_adjustment=-round(reduction, 2),
            )
        if exclusions:
            return TriggeredRule(
                code="EXCLUDED_TREATMENT",
                category=RuleCategory.COVERAGE_VALIDATION,
                passed=False,
                explanation=f"Diagnosis contains excluded treatment category: {', '.join(exclusions)}.",
            )
        return TriggeredRule(
            code="COVERED_OPD_SERVICE",
            category=RuleCategory.COVERAGE_VALIDATION,
            passed=True,
            explanation="No configured OPD exclusion matched the extracted diagnosis.",
        )

    def _network_rule(self, hospital_name: str, network_status: str) -> TriggeredRule:
        if network_status == "OUT_OF_NETWORK" and hospital_name not in self.policy.network_providers():
            return TriggeredRule(
                code="OUT_OF_NETWORK_PROVIDER",
                category=RuleCategory.COVERAGE_VALIDATION,
                passed=False,
                explanation="Provider is outside the configured network for this OPD policy.",
            )
        return TriggeredRule(
            code="NETWORK_PROVIDER_VALID",
            category=RuleCategory.COVERAGE_VALIDATION,
            passed=True,
            explanation="Provider network rule passed.",
        )

    def _medical_necessity_rule(
        self,
        diagnosis: str | None,
        medicines: list[str],
        procedures: list[str],
        tests: list[str],
    ) -> TriggeredRule:
        if not diagnosis:
            return TriggeredRule(
                code="MEDICAL_NECESSITY_UNVERIFIABLE",
                category=RuleCategory.MEDICAL_NECESSITY,
                passed=False,
                explanation="Medical necessity cannot be verified because diagnosis was not extracted.",
            )
        if diagnosis and (medicines or procedures or tests):
            return TriggeredRule(
                code="MEDICAL_NECESSITY_PRESENT",
                category=RuleCategory.MEDICAL_NECESSITY,
                passed=True,
                explanation="Diagnosis and treatment details support OPD medical necessity.",
            )
        return TriggeredRule(
            code="MEDICAL_NECESSITY_NOT_ESTABLISHED",
            category=RuleCategory.MEDICAL_NECESSITY,
            passed=False,
            explanation="Claim lacks diagnosis or treatment details needed to establish medical necessity.",
        )

    def _limit_rules(self, fields, annual_claimed_amount: float) -> tuple[list[TriggeredRule], float]:
        approved_amount = fields.bill_amount
        remaining_annual = max(0, self.policy.annual_limit() - annual_claimed_amount)
        approved_amount = min(approved_amount, remaining_annual)

        rules: list[TriggeredRule] = []
        if fields.bill_amount > self.policy.per_claim_limit():
            rules.append(
                TriggeredRule(
                    code="PER_CLAIM_LIMIT_EXCEEDED",
                    category=RuleCategory.LIMIT_VALIDATION,
                    passed=False,
                    explanation=(
                        f"Claim amount Rs {fields.bill_amount:.0f} exceeds per-claim limit "
                        f"of Rs {self.policy.per_claim_limit():.0f}."
                    ),
                )
            )
            approved_amount = 0
        else:
            rules.append(
                TriggeredRule(
                    code="PER_CLAIM_LIMIT_WITHIN_LIMIT",
                    category=RuleCategory.LIMIT_VALIDATION,
                    passed=True,
                    explanation="Claim amount is within the configured per-claim limit.",
                )
            )

        category_caps = [
            ("consultation", fields.consultation_amount),
            ("pharmacy", fields.pharmacy_amount),
            ("diagnostics", fields.diagnostic_amount),
        ]
        for category, amount in category_caps:
            cap = self.policy.category_limit(category)
            if amount > cap > 0:
                approved_amount -= amount - cap
                rules.append(
                    TriggeredRule(
                        code=f"{category.upper()}_SUB_LIMIT_EXCEEDED",
                        category=RuleCategory.LIMIT_VALIDATION,
                        passed=True,
                        explanation=f"{category.title()} amount Rs {amount:.0f} exceeds sub-limit of Rs {cap:.0f}.",
                        amount_adjustment=cap - amount,
                    )
                )

        if remaining_annual <= 0:
            rules.append(
                TriggeredRule(
                    code="ANNUAL_LIMIT_EXHAUSTED",
                    category=RuleCategory.LIMIT_VALIDATION,
                    passed=False,
                    explanation="Annual OPD limit is already exhausted.",
                )
            )
        elif fields.bill_amount > remaining_annual:
            rules.append(
                TriggeredRule(
                    code="ANNUAL_LIMIT_PARTIAL_AVAILABLE",
                    category=RuleCategory.LIMIT_VALIDATION,
                    passed=True,
                    explanation=f"Only Rs {remaining_annual:.0f} remains under the annual OPD limit.",
                    amount_adjustment=remaining_annual - fields.bill_amount,
                )
            )

        return rules, max(0, approved_amount)

    def _decision_from_rules(
        self,
        rules: list[TriggeredRule],
        approved_amount: float,
        confidence_score: float,
        fraud_findings,
        missing_required_fields: int,
    ) -> Decision:
        rejection_codes = {
            "WAITING_PERIOD_NOT_SERVED",
            "REQUIRED_DOCUMENTS_MISSING",
            "EXCLUDED_TREATMENT",
            "PER_CLAIM_LIMIT_EXCEEDED",
            "OUT_OF_NETWORK_PROVIDER",
            "MEDICAL_NECESSITY_NOT_ESTABLISHED",
            "ANNUAL_LIMIT_EXHAUSTED",
        }
        if any((not rule.passed and rule.code in rejection_codes) for rule in rules):
            return Decision.REJECTED
        if fraud_findings or confidence_score < 70 or missing_required_fields:
            return Decision.MANUAL_REVIEW
        if approved_amount <= 0:
            return Decision.REJECTED
        if any(rule.amount_adjustment is not None and rule.amount_adjustment < 0 for rule in rules):
            return Decision.PARTIAL
        return Decision.APPROVED

    @staticmethod
    def _has_required_documents(document_types: list[str]) -> bool:
        normalized = {item.upper() for item in document_types}
        return {"PRESCRIPTION", "MEDICAL_BILL"}.issubset(normalized)

    @staticmethod
    def _missing_required_fields_count(claim: ClaimAdjudicationInput) -> int:
        fields = claim.extracted_fields
        required_values = [
            fields.patient_name,
            fields.doctor_name,
            fields.doctor_registration_number,
            fields.diagnosis,
            fields.treatment_date,
            fields.hospital_name,
            fields.bill_amount,
        ]
        return sum(1 for value in required_values if not value)
