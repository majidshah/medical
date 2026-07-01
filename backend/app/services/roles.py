"""Role/permission service.

Extensible by design: a role is a row in `roles`, a grant is a row in
`account_roles`. Adding a future role (clinician/kiosk/...) is a data
change, not a schema change. There is exactly one grant write path —
grant_role() — called from either the admin-only HTTP endpoint (the
caller already passed require_admin) or the CLI bootstrap script (run
directly by a human, never over HTTP). No code path lets an account
grant itself a role.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.account_role import AccountRole
from app.models.role import Role
from app.services.audit import log_event

ADMIN_ROLE_KEY = "admin"


class RoleError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


async def get_role_keys(session: AsyncSession, account_id: uuid.UUID) -> set[str]:
    result = await session.execute(
        select(Role.key)
        .join(AccountRole, AccountRole.role_id == Role.id)
        .where(AccountRole.account_id == account_id)
    )
    return set(result.scalars().all())


async def has_role(session: AsyncSession, account_id: uuid.UUID, role_key: str) -> bool:
    keys = await get_role_keys(session, account_id)
    return role_key in keys


async def is_admin(session: AsyncSession, account_id: uuid.UUID) -> bool:
    return await has_role(session, account_id, ADMIN_ROLE_KEY)


async def grant_role(
    session: AsyncSession,
    *,
    target_email: str,
    role_key: str,
    granted_by_account_id: uuid.UUID | None,
) -> AccountRole:
    """Grant `role_key` to the account with `target_email`.

    Idempotent: granting a role the account already has returns the
    existing grant without creating a duplicate row or an audit entry.

    granted_by_account_id is None only for the CLI bootstrap path — every
    HTTP-triggered grant passes the acting admin's account id.
    """
    role = (await session.execute(select(Role).where(Role.key == role_key))).scalar_one_or_none()
    if role is None:
        raise RoleError(f"Unknown role: {role_key}", status_code=404)

    target = (
        await session.execute(select(Account).where(Account.email == target_email.lower()))
    ).scalar_one_or_none()
    if target is None:
        raise RoleError("Account not found", status_code=404)

    existing = (
        await session.execute(
            select(AccountRole).where(
                AccountRole.account_id == target.id, AccountRole.role_id == role.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    grant = AccountRole(
        account_id=target.id, role_id=role.id, granted_by_account_id=granted_by_account_id
    )
    session.add(grant)
    await session.flush()
    await log_event(
        session,
        "admin.role_granted",
        account_id=granted_by_account_id,
        detail=f"target_account_id={target.id} role_key={role_key}",
    )
    await session.commit()
    return grant
