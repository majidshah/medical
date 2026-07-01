from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.account import Account
from app.models.role import Role
from app.schemas.roles import AccountRoleResponse, GrantRoleRequest, RoleResponse
from app.services.roles import RoleError, grant_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Role]:
    result = await session.execute(select(Role).order_by(Role.key))
    return list(result.scalars().all())


@router.post("/roles/grant", response_model=AccountRoleResponse, status_code=201)
async def grant_role_endpoint(
    body: GrantRoleRequest,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccountRoleResponse:
    try:
        grant = await grant_role(
            session,
            target_email=body.email,
            role_key=body.role_key,
            granted_by_account_id=admin.id,
        )
    except RoleError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return AccountRoleResponse.model_validate(grant)
