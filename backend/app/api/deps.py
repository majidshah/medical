import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.account import Account
from app.services.auth import get_account_by_id
from app.services.roles import is_admin

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Account:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    try:
        account_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None

    account = await get_account_by_id(session, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")

    return account


async def require_admin(
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Account:
    """Admin is a distinct authorization boundary layered on top of
    get_current_account, not a substitute for it. A request reaches here
    only after passing authentication; 403 (not 404) is correct — the
    endpoint exists, the caller is a known account, they just lack the
    permission. This is deliberately different from the patient-data
    404-not-403 rule, which exists to avoid leaking whether another
    account's data exists at all.
    """
    if not await is_admin(session, account.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return account
