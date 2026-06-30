import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountRole(Base):
    """Grants `role_id` to `account_id`. Existence of a row IS the grant.

    Rows are only ever created by app.services.roles.grant_role, which is
    called from either the admin-only grant endpoint (require_admin already
    verified the caller) or the one-off bootstrap CLI (scripts/grant_admin.py,
    run directly by a human — never reachable over HTTP). There is no other
    write path; account_id alone is never sufficient to create a row here.
    """

    __tablename__ = "account_roles"
    __table_args__ = (
        UniqueConstraint("account_id", "role_id", name="uq_account_roles_account_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), index=True, nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), index=True, nullable=False
    )
    # Which account performed the grant. NULL means it was granted via the
    # CLI bootstrap script (no acting account — that's the point: the very
    # first admin can't be granted "by" an existing admin).
    granted_by_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
