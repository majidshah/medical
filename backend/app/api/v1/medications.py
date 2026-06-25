import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.medication import to_fhir
from app.models.account import Account
from app.schemas.medication import (
    MedicationCreate,
    MedicationListResponse,
    MedicationResponse,
    MedicationUpdate,
)
from app.services.medication import (
    MedicationError,
    create_medication,
    get_medication,
    list_medications,
    soft_delete_medication,
    update_medication,
)

router = APIRouter(prefix="/patients/{patient_id}/medications", tags=["medications"])


@router.post("", response_model=MedicationResponse, status_code=201)
async def create(
    patient_id: uuid.UUID,
    body: MedicationCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MedicationResponse:
    try:
        medication = await create_medication(
            session,
            patient_id,
            account.id,
            display_name=body.display_name,
            code=body.code,
            code_system=body.code_system,
            dosage=body.dosage,
            frequency=body.frequency,
            route=body.route,
            status=body.status.value,
            start_date=body.start_date,
            end_date=body.end_date,
            prescribed_by=body.prescribed_by,
            notes=body.notes,
        )
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return MedicationResponse.model_validate(medication)


@router.get("", response_model=MedicationListResponse)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MedicationListResponse:
    try:
        items, total = await list_medications(
            session, patient_id, account.id, limit=limit, offset=offset
        )
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return MedicationListResponse(
        items=[MedicationResponse.model_validate(m) for m in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_one(
    patient_id: uuid.UUID,
    medication_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MedicationResponse:
    try:
        medication = await get_medication(session, medication_id, patient_id, account.id)
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if medication is None:
        raise HTTPException(status_code=404, detail="Medication not found")
    return MedicationResponse.model_validate(medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def patch(
    patient_id: uuid.UUID,
    medication_id: uuid.UUID,
    body: MedicationUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MedicationResponse:
    fields = body.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] is not None:
        fields["status"] = fields["status"].value
    try:
        medication = await update_medication(
            session, medication_id, patient_id, account.id, **fields
        )
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return MedicationResponse.model_validate(medication)


@router.delete("/{medication_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    medication_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_medication(session, medication_id, patient_id, account.id)
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/{medication_id}/fhir")
async def get_fhir(
    patient_id: uuid.UUID,
    medication_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        medication = await get_medication(session, medication_id, patient_id, account.id)
    except MedicationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if medication is None:
        raise HTTPException(status_code=404, detail="Medication not found")
    return to_fhir(medication, patient_id)
