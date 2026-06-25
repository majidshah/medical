import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.condition import to_fhir
from app.models.account import Account
from app.schemas.condition import (
    ConditionCreate,
    ConditionListResponse,
    ConditionResponse,
    ConditionUpdate,
)
from app.services.condition import (
    ConditionError,
    create_condition,
    get_condition,
    list_conditions,
    soft_delete_condition,
    update_condition,
)

router = APIRouter(prefix="/patients/{patient_id}/conditions", tags=["conditions"])


@router.post("", response_model=ConditionResponse, status_code=201)
async def create(
    patient_id: uuid.UUID,
    body: ConditionCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConditionResponse:
    try:
        condition = await create_condition(
            session,
            patient_id,
            account.id,
            display_name=body.display_name,
            code=body.code,
            code_system=body.code_system,
            clinical_status=body.clinical_status.value,
            onset_date=body.onset_date,
            abatement_date=body.abatement_date,
            notes=body.notes,
        )
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ConditionResponse.model_validate(condition)


@router.get("", response_model=ConditionListResponse)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ConditionListResponse:
    try:
        items, total = await list_conditions(
            session, patient_id, account.id, limit=limit, offset=offset
        )
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ConditionListResponse(
        items=[ConditionResponse.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{condition_id}", response_model=ConditionResponse)
async def get_one(
    patient_id: uuid.UUID,
    condition_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConditionResponse:
    try:
        condition = await get_condition(session, condition_id, patient_id, account.id)
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if condition is None:
        raise HTTPException(status_code=404, detail="Condition not found")
    return ConditionResponse.model_validate(condition)


@router.patch("/{condition_id}", response_model=ConditionResponse)
async def patch(
    patient_id: uuid.UUID,
    condition_id: uuid.UUID,
    body: ConditionUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConditionResponse:
    fields = body.model_dump(exclude_unset=True)
    if "clinical_status" in fields and fields["clinical_status"] is not None:
        fields["clinical_status"] = fields["clinical_status"].value
    try:
        condition = await update_condition(session, condition_id, patient_id, account.id, **fields)
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ConditionResponse.model_validate(condition)


@router.delete("/{condition_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    condition_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_condition(session, condition_id, patient_id, account.id)
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/{condition_id}/fhir")
async def get_fhir(
    patient_id: uuid.UUID,
    condition_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        condition = await get_condition(session, condition_id, patient_id, account.id)
    except ConditionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if condition is None:
        raise HTTPException(status_code=404, detail="Condition not found")
    return to_fhir(condition, patient_id)
