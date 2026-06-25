import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.account import Account
from app.models.refresh_token import RefreshToken
from app.services.audit import log_event


class AuthError(Exception):
    def __init__(self, detail: str, status_code: int = 401):
        self.detail = detail
        self.status_code = status_code


async def register_account(session: AsyncSession, email: str, password: str) -> Account:
    email_lower = email.lower()
    existing = await session.execute(select(Account).where(Account.email == email_lower))
    if existing.scalar_one_or_none() is not None:
        raise AuthError("An account with this email already exists", status_code=409)

    account = Account(email=email_lower, password_hash=hash_password(password))
    session.add(account)
    await session.flush()
    await log_event(session, "account_created", account_id=account.id)
    await session.commit()
    return account


async def login(session: AsyncSession, email: str, password: str) -> tuple[Account, str, str]:
    email_lower = email.lower()
    result = await session.execute(select(Account).where(Account.email == email_lower))
    account = result.scalar_one_or_none()

    if account is None:
        verify_password(password, DUMMY_HASH)
        raise AuthError("Invalid credentials")

    if not verify_password(password, account.password_hash):
        await log_event(session, "login_failure", account_id=account.id)
        await session.commit()
        raise AuthError("Invalid credentials")

    if not account.is_active:
        raise AuthError("Account is inactive")

    access_token = create_access_token(account.id)
    raw_refresh, token_hash, expires_at = create_refresh_token(account.id)

    refresh_row = RefreshToken(account_id=account.id, token_hash=token_hash, expires_at=expires_at)
    session.add(refresh_row)
    await log_event(session, "login_success", account_id=account.id)
    await session.commit()

    return account, access_token, raw_refresh


async def refresh_tokens(session: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
    token_hash = hash_token(raw_refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked_at is not None:
        raise AuthError("Invalid refresh token")

    if stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise AuthError("Refresh token expired")

    account_result = await session.execute(
        select(Account).where(Account.id == stored.account_id, Account.is_active.is_(True))
    )
    account = account_result.scalar_one_or_none()
    if account is None:
        raise AuthError("Account not found or inactive")

    stored.revoked_at = datetime.now(UTC)

    access_token = create_access_token(account.id)
    raw_new_refresh, new_hash, new_expires = create_refresh_token(account.id)
    new_row = RefreshToken(account_id=account.id, token_hash=new_hash, expires_at=new_expires)
    session.add(new_row)
    await log_event(session, "token_refreshed", account_id=account.id)
    await session.commit()

    return access_token, raw_new_refresh


async def logout(session: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_token(raw_refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked_at is not None:
        raise AuthError("Invalid refresh token")

    stored.revoked_at = datetime.now(UTC)

    await log_event(session, "logout", account_id=stored.account_id)
    await session.commit()


async def get_account_by_id(session: AsyncSession, account_id: uuid.UUID) -> Account | None:
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.is_active.is_(True))
    )
    return result.scalar_one_or_none()
