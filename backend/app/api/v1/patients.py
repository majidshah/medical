import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient import (
    PatientError,
    create_patient,
    get_patient,
    list_patients,
    search_patient_by_medical_id,
    soft_delete_patient,
    update_patient,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=201)
async def create(
    body: PatientCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PatientResponse:
    try:
        patient = await create_patient(
            session,
            account.id,
            full_name=body.full_name,
            date_of_birth=body.date_of_birth,
            gender=body.gender.value,
            relationship_to_account=body.relationship_to_account.value,
            cnic=body.cnic,
            guardian_patient_id=body.guardian_patient_id,
        )
    except PatientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return PatientResponse.model_validate(patient)


@router.get("", response_model=PatientListResponse)
async def list_all(
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PatientListResponse:
    patients, total = await list_patients(session, account.id, limit=limit, offset=offset)
    return PatientListResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=PatientResponse | None)
async def search(
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    medical_id: str = Query(),
) -> PatientResponse | None:
    patient = await search_patient_by_medical_id(session, account.id, medical_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_one(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PatientResponse:
    patient = await get_patient(session, patient_id, account.id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def patch(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PatientResponse:
    fields = body.model_dump(exclude_unset=True)
    if "gender" in fields and fields["gender"] is not None:
        fields["gender"] = fields["gender"].value
    if "relationship_to_account" in fields and fields["relationship_to_account"] is not None:
        fields["relationship_to_account"] = fields["relationship_to_account"].value
    try:
        patient = await update_patient(session, patient_id, account.id, **fields)
    except PatientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_patient(session, patient_id, account.id)
    except PatientError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
