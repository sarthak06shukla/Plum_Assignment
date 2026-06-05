from datetime import date

from pydantic import BaseModel, Field


class ExtractedClaimFields(BaseModel):
    patient_name: str | None = None
    patient_age: int | None = Field(default=None, ge=0, le=120)
    doctor_name: str | None = None
    doctor_registration_number: str | None = None
    diagnosis: str | None = None
    medicines: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    treatment_date: date | None = None
    hospital_name: str | None = None
    bill_amount: float = Field(default=0, ge=0)
    consultation_amount: float = Field(default=0, ge=0)
    pharmacy_amount: float = Field(default=0, ge=0)
    diagnostic_amount: float = Field(default=0, ge=0)


class ExtractionResult(BaseModel):
    fields: ExtractedClaimFields
    confidence_score: float = Field(ge=0, le=100)
    missing_fields: list[str] = Field(default_factory=list)
