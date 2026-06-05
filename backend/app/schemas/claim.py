from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProcessingStage(BaseModel):
    name: str
    status: str
    detail: str | None = None
    progress: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    confidence_score: float | None = None


class ClaimSummary(BaseModel):
    id: str
    patient_name: str | None
    status: str
    claimed_amount: float
    approved_amount: float
    confidence_score: float
    created_at: datetime


class ClaimDetail(ClaimSummary):
    documents: list[dict[str, Any]]
    extracted_information: dict[str, Any] | None
    policy_evaluation: list[dict[str, Any]]
    audit_trail: list[dict[str, Any]]
    fraud_signals: list[dict[str, Any]]
    decision_explanation: str | None
