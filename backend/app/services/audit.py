import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_event(
    session: AsyncSession,
    event_type: str,
    account_id: uuid.UUID | None = None,
    detail: str | None = None,
) -> None:
    entry = AuditLog(account_id=account_id, event_type=event_type, detail=detail)
    session.add(entry)
    await session.flush()
