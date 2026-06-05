from backend.app.schemas.decision import Decision, RuleDecision


class DecisionExplanationService:
    def explain(self, decision: RuleDecision) -> str:
        failed_rules = [rule for rule in decision.triggered_rules if not rule.passed]
        adjusted_rules = [rule for rule in decision.triggered_rules if rule.amount_adjustment is not None]
        if failed_rules:
            primary = failed_rules[0]
            return self._format(
                decision=decision.decision,
                reason=primary.explanation,
                impact=self._impact(decision.decision),
                action=self._recommended_action(decision.decision),
            )

        if adjusted_rules:
            primary = adjusted_rules[0]
            return self._format(
                decision=decision.decision,
                reason=primary.explanation,
                impact=f"Only Rs {decision.approved_amount:.0f} is payable under current policy terms.",
                action="Review excluded or capped line items before payout.",
            )

        amount = f"Rs {decision.approved_amount:.0f}"
        return self._format(
            decision=decision.decision,
            reason="Claim passed eligibility, document, coverage, limit, medical necessity and fraud checks.",
            impact=f"Approved amount is {amount}.",
            action="Proceed with reimbursement processing.",
        )

    @staticmethod
    def _label(decision: Decision) -> str:
        if decision == Decision.PARTIAL:
            return "Partial"
        return decision.value.replace("_", " ").title()

    def _format(self, *, decision: Decision, reason: str, impact: str, action: str) -> str:
        return (
            f"Decision: {self._label(decision)}\n"
            f"Reason: {reason}\n"
            f"Impact: {impact}\n"
            f"Recommended Action: {action}"
        )

    @staticmethod
    def _impact(decision: Decision) -> str:
        impacts = {
            Decision.REJECTED: "Claim cannot be reimbursed under current policy terms.",
            Decision.MANUAL_REVIEW: "Claim requires human review before payout.",
            Decision.PARTIAL: "Only covered or within-limit components can be reimbursed.",
            Decision.PARTIAL_APPROVAL: "Only covered or within-limit components can be reimbursed.",
        }
        return impacts.get(decision, "Claim is eligible for reimbursement.")

    @staticmethod
    def _recommended_action(decision: Decision) -> str:
        actions = {
            Decision.REJECTED: "Submit corrected documents or covered expenses within allowed policy terms.",
            Decision.MANUAL_REVIEW: "Reviewer should verify documents, extracted fields and fraud signals.",
            Decision.PARTIAL: "Confirm payable components and communicate the non-payable portion.",
            Decision.PARTIAL_APPROVAL: "Confirm payable components and communicate the non-payable portion.",
        }
        return actions.get(decision, "Proceed with reimbursement processing.")
