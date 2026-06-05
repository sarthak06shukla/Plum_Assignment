from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from backend.app.schemas.extraction import ExtractedClaimFields


class Decision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    PARTIAL_APPROVAL = "PARTIAL_APPROVAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RuleCategory(StrEnum):
    ELIGIBILITY = "Eligibility"
    DOCUMENT_VALIDATION = "Document Validation"
    COVERAGE_VALIDATION = "Coverage Validation"
    LIMIT_VALIDATION = "Limit Validation"
    MEDICAL_NECESSITY = "Medical Necessity"
    FRAUD_CHECKS = "Fraud Checks"


class TriggeredRule(BaseModel):
    code: str
    category: RuleCategory
    passed: bool
    explanation: str
    amount_adjustment: float | None = None


class FraudFinding(BaseModel):
    code: str
    severity: str
    description: str


class ClaimHistoryItem(BaseModel):
    claim_id: str
    patient_name: str
    treatment_date: date | None = None
    bill_amount: float = 0
    doctor_registration_number: str | None = None
    status: str = "SUBMITTED"
    created_at: date | None = None


class PolicyContext(BaseModel):
    member_id: str
    policy_start_date: date
    annual_claimed_amount: float = 0
    provider_network_status: str = "IN_NETWORK"


class ClaimAdjudicationInput(BaseModel):
    extracted_fields: ExtractedClaimFields
    document_types: list[str]
    ocr_confidence: float
    extraction_confidence: float
    policy_context: PolicyContext
    claim_history: list[ClaimHistoryItem] = Field(default_factory=list)


class RuleDecision(BaseModel):
    decision: Decision
    approved_amount: float
    triggered_rules: list[TriggeredRule]
    notes: list[str] = Field(default_factory=list)
    fraud_findings: list[FraudFinding] = Field(default_factory=list)
    confidence_score: float = 0
    explanation: str = ""
    policy_snapshot: dict[str, Any] = Field(default_factory=dict)
