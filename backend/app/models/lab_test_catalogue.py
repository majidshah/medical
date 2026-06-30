import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabTestCatalogue(Base):
    __tablename__ = "lab_test_catalogue"
    __table_args__ = (
        # A test's panel (if any) must belong to the test's own department.
        # Enforced at the DB level: Postgres skips a multi-column FK check
        # when any referencing column is NULL, so this constraint is a
        # no-op for standalone tests (panel_id IS NULL) and is fully
        # enforced once a panel is assigned.
        ForeignKeyConstraint(
            ["department_id", "panel_id"],
            ["lab_panels.department_id", "lab_panels.id"],
            name="fk_lab_test_catalogue_panel_matches_department",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    specimen: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_departments.id"), index=True, nullable=False
    )
    panel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_panels.id"), index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
