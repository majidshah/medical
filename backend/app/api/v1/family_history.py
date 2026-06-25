import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.family_history import to_fhir
from app.models.account import Account
from app.schemas.family_history import (
    FamilyHistoryCreate,
    FamilyHistoryListResponse,
    FamilyHistoryResponse,
    FamilyHistoryUpdate,
)
from app.services.family_history import (
    FamilyHistoryError,
    create_family_history,
    get_family_history,
    list_family_histories,
    soft_delete_family_history,
    update_family_history,
)

router = APIRouter(prefix="/patients/{patient_id}/family-history", tags=["family-history"])


@router.post("", response_model=FamilyHistoryResponse, status_code=201)
async def create(
    patient_id: uuid.UUID,
    body: FamilyHistoryCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyHistoryResponse:
    try:
        fh = await create_family_history(
            session,
            patient_id,
            account.id,
            relationship=body.relationship.value,
            condition_display_name=body.condition_display_name,
            condition_code=body.condition_code,
            condition_code_system=body.condition_code_system,
            onset_age=body.onset_age,
            deceased=body.deceased,
            notes=body.notes,
        )
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return FamilyHistoryResponse.model_validate(fh)


@router.get("", response_model=FamilyHistoryListResponse)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FamilyHistoryListResponse:
    try:
        items, total = await list_family_histories(
            session, patient_id, account.id, limit=limit, offset=offset
        )
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return FamilyHistoryListResponse(
        items=[FamilyHistoryResponse.model_validate(fh) for fh in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{family_history_id}", response_model=FamilyHistoryResponse)
async def get_one(
    patient_id: uuid.UUID,
    family_history_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyHistoryResponse:
    try:
        fh = await get_family_history(session, family_history_id, patient_id, account.id)
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if fh is None:
        raise HTTPException(status_code=404, detail="Family history not found")
    return FamilyHistoryResponse.model_validate(fh)


@router.patch("/{family_history_id}", response_model=FamilyHistoryResponse)
async def patch(
    patient_id: uuid.UUID,
    family_history_id: uuid.UUID,
    body: FamilyHistoryUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FamilyHistoryResponse:
    fields = body.model_dump(exclude_unset=True)
    if "relationship" in fields and fields["relationship"] is not None:
        fields["relationship"] = fields["relationship"].value
    try:
        fh = await update_family_history(
            session, family_history_id, patient_id, account.id, **fields
        )
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return FamilyHistoryResponse.model_validate(fh)


@router.delete("/{family_history_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    family_history_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_family_history(session, family_history_id, patient_id, account.id)
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/{family_history_id}/fhir")
async def get_fhir(
    patient_id: uuid.UUID,
    family_history_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        fh = await get_family_history(session, family_history_id, patient_id, account.id)
    except FamilyHistoryError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if fh is None:
        raise HTTPException(status_code=404, detail="Family history not found")
    return to_fhir(fh, patient_id)
