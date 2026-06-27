import json
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.schemas.preferences import ThemePreferences

router = APIRouter(prefix="/account", tags=["preferences"])

DEFAULTS = ThemePreferences()


@router.get("/preferences", response_model=ThemePreferences)
async def get_preferences(
    account: Annotated[Account, Depends(get_current_account)],
) -> ThemePreferences:
    if account.theme_preferences:
        return ThemePreferences(**json.loads(account.theme_preferences))
    return DEFAULTS


@router.put("/preferences", response_model=ThemePreferences)
async def update_preferences(
    body: ThemePreferences,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThemePreferences:
    account.theme_preferences = json.dumps(body.model_dump())
    await session.flush()
    await session.commit()
    return body
