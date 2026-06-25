import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FamilyHistory(Base):
    __tablename__ = "family_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True, nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), index=True, nullable=False
    )
    relationship: Mapped[str] = mapped_column(Text, nullable=False)
    condition_code_system: Mapped[str] = mapped_column(
        Text, default="http://snomed.info/sct", nullable=False
    )
    condition_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    onset_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deceased: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
