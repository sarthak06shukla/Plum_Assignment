from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class ClaimStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    PARTIAL_APPROVAL = "PARTIAL_APPROVAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class DocumentType(StrEnum):
    PRESCRIPTION = "PRESCRIPTION"
    MEDICAL_BILL = "MEDICAL_BILL"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claims: Mapped[list["Claim"]] = relationship(back_populates="user")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    patient_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.SUBMITTED)
    claimed_amount: Mapped[float] = mapped_column(Float, default=0)
    approved_amount: Mapped[float] = mapped_column(Float, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0)
    processing_stage: Mapped[str] = mapped_column(String, default="Document Upload")
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="claims")
    documents: Mapped[list["Document"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    extracted_fields: Mapped["ExtractedFields | None"] = relationship(back_populates="claim", cascade="all, delete-orphan")
    decision_logs: Mapped[list["DecisionLog"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    fraud_flags: Mapped[list["FraudFlag"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    manual_reviews: Mapped[list["ManualReview"]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    filename: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    file_size: Mapped[int] = mapped_column(Integer)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="documents")


class ExtractedFields(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), unique=True)
    fields: Mapped[dict[str, Any]] = mapped_column(JSON)
    extraction_confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="extracted_fields")


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    decision: Mapped[str] = mapped_column(String)
    triggered_rule: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="decision_logs")


class FraudFlag(Base):
    __tablename__ = "fraud_flags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    code: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="fraud_flags")


class ManualReview(Base):
    __tablename__ = "manual_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    reason: Mapped[str] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(String, nullable=True)
    override_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    claim: Mapped[Claim] = relationship(back_populates="manual_reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
