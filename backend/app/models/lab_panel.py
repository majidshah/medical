import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabPanel(Base):
    __tablename__ = "lab_panels"
    __table_args__ = (
        UniqueConstraint("department_id", "key", name="uq_lab_panels_department_id_key"),
        # Composite-unique target so lab_test_catalogue can FK on
        # (department_id, panel_id) and have Postgres enforce that a
        # test's panel actually belongs to the test's department.
        UniqueConstraint("department_id", "id", name="uq_lab_panels_department_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_departments.id"), index=True, nullable=False
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
