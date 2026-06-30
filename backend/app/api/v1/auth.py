from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.schemas.auth import (
    AccountResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth import AuthError, refresh_tokens, register_account
from app.services.auth import login as login_service
from app.services.auth import logout as logout_service
from app.services.roles import get_role_keys

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AccountResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Account:
    try:
        return await register_account(session, body.email, body.password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    try:
        _account, access_token, refresh_token = await login_service(
            session, body.email, body.password
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    try:
        access_token, refresh_token = await refresh_tokens(session, body.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await logout_service(session, body.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/me", response_model=AccountResponse)
async def me(
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountResponse:
    roles = await get_role_keys(session, account.id)
    return AccountResponse(id=account.id, email=account.email, roles=sorted(roles))
