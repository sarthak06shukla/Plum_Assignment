import json
from functools import cached_property
from typing import Any

from backend.app.core.config import get_settings


class PolicyEngine:
    @cached_property
    def policy(self) -> dict[str, Any]:
        path = get_settings().policy_config_path
        return json.loads(path.read_text(encoding="utf-8"))

    def annual_limit(self) -> float:
        return float(self.policy["annual_limit"])

    def per_claim_limit(self) -> float:
        return float(self.policy["per_claim_limit"])

    def waiting_period_days(self) -> int:
        return int(self.policy["waiting_period_days"])

    def category_limit(self, category: str) -> float:
        return float(self.policy["category_sub_limits"].get(category, 0))

    def covered_services(self) -> set[str]:
        return {item.lower() for item in self.policy["covered_services"]}

    def exclusions(self) -> set[str]:
        return {item.lower() for item in self.policy["exclusions"]}

    def network_providers(self) -> set[str]:
        return set(self.policy["network_providers"])

    def mixed_exclusion_reduction_percent(self) -> float:
        return float(self.policy.get("mixed_exclusion_reduction_percent", 0))

    def auto_approve_threshold(self) -> float:
        return float(self.policy.get("auto_approve_threshold", self.policy.get("manual_review_threshold", 70)))

    def auto_reject_threshold(self) -> float:
        return float(self.policy.get("auto_reject_threshold", 50))

    def snapshot(self) -> dict[str, Any]:
        return self.policy
