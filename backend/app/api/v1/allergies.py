import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.allergy import to_fhir
from app.models.account import Account
from app.schemas.allergy import (
    AllergyCreate,
    AllergyListResponse,
    AllergyResponse,
    AllergyUpdate,
)
from app.services.allergy import (
    AllergyError,
    create_allergy,
    get_allergy,
    list_allergies,
    soft_delete_allergy,
    update_allergy,
)

router = APIRouter(prefix="/patients/{patient_id}/allergies", tags=["allergies"])


@router.post("", response_model=AllergyResponse, status_code=201)
async def create(
    patient_id: uuid.UUID,
    body: AllergyCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AllergyResponse:
    try:
        allergy = await create_allergy(
            session,
            patient_id,
            account.id,
            display_name=body.display_name,
            code=body.code,
            code_system=body.code_system,
            category=body.category.value,
            criticality=body.criticality.value if body.criticality else None,
            clinical_status=body.clinical_status.value,
            reaction=body.reaction,
            severity=body.severity.value if body.severity else None,
            onset_date=body.onset_date,
            notes=body.notes,
        )
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return AllergyResponse.model_validate(allergy)


@router.get("", response_model=AllergyListResponse)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AllergyListResponse:
    try:
        items, total = await list_allergies(
            session, patient_id, account.id, limit=limit, offset=offset
        )
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return AllergyListResponse(
        items=[AllergyResponse.model_validate(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{allergy_id}", response_model=AllergyResponse)
async def get_one(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AllergyResponse:
    try:
        allergy = await get_allergy(session, allergy_id, patient_id, account.id)
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if allergy is None:
        raise HTTPException(status_code=404, detail="Allergy not found")
    return AllergyResponse.model_validate(allergy)


@router.patch("/{allergy_id}", response_model=AllergyResponse)
async def patch(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    body: AllergyUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AllergyResponse:
    fields = body.model_dump(exclude_unset=True)
    for enum_field in ("category", "criticality", "clinical_status", "severity"):
        if enum_field in fields and fields[enum_field] is not None:
            fields[enum_field] = fields[enum_field].value
    try:
        allergy = await update_allergy(session, allergy_id, patient_id, account.id, **fields)
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return AllergyResponse.model_validate(allergy)


@router.delete("/{allergy_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_allergy(session, allergy_id, patient_id, account.id)
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/{allergy_id}/fhir")
async def get_fhir(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        allergy = await get_allergy(session, allergy_id, patient_id, account.id)
    except AllergyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if allergy is None:
        raise HTTPException(status_code=404, detail="Allergy not found")
    return to_fhir(allergy, patient_id)
