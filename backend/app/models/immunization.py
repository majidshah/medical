import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Immunization(Base):
    __tablename__ = "immunizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), index=True, nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), index=True, nullable=False
    )
    epi_vaccine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epi_vaccines.id"), nullable=True
    )
    vaccine_display_name: Mapped[str] = mapped_column(Text, nullable=False)
    code_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    dose_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
    lot_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(Text, nullable=True)
    site: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="completed", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
