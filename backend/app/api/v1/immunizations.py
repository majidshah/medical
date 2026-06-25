import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.immunization import to_fhir
from app.models.account import Account
from app.schemas.immunization import (
    EPIVaccineResponse,
    ImmunizationCreate,
    ImmunizationListResponse,
    ImmunizationResponse,
    ImmunizationUpdate,
)
from app.services.immunization import (
    ImmunizationError,
    create_immunization,
    get_immunization,
    list_epi_vaccines,
    list_immunizations,
    soft_delete_immunization,
    update_immunization,
)

router = APIRouter(tags=["immunizations"])


@router.post(
    "/patients/{patient_id}/immunizations",
    response_model=ImmunizationResponse,
    status_code=201,
)
async def create(
    patient_id: uuid.UUID,
    body: ImmunizationCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImmunizationResponse:
    try:
        imm = await create_immunization(
            session,
            patient_id,
            account.id,
            vaccine_display_name=body.vaccine_display_name,
            epi_vaccine_id=body.epi_vaccine_id,
            code=body.code,
            code_system=body.code_system,
            dose_number=body.dose_number,
            occurrence_date=body.occurrence_date,
            lot_number=body.lot_number,
            manufacturer=body.manufacturer,
            site=body.site,
            status=body.status.value,
            notes=body.notes,
        )
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ImmunizationResponse.model_validate(imm)


@router.get("/patients/{patient_id}/immunizations", response_model=ImmunizationListResponse)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ImmunizationListResponse:
    try:
        items, total = await list_immunizations(
            session, patient_id, account.id, limit=limit, offset=offset
        )
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ImmunizationListResponse(
        items=[ImmunizationResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/patients/{patient_id}/immunizations/{immunization_id}",
    response_model=ImmunizationResponse,
)
async def get_one(
    patient_id: uuid.UUID,
    immunization_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImmunizationResponse:
    try:
        imm = await get_immunization(session, immunization_id, patient_id, account.id)
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if imm is None:
        raise HTTPException(status_code=404, detail="Immunization not found")
    return ImmunizationResponse.model_validate(imm)


@router.patch(
    "/patients/{patient_id}/immunizations/{immunization_id}",
    response_model=ImmunizationResponse,
)
async def patch(
    patient_id: uuid.UUID,
    immunization_id: uuid.UUID,
    body: ImmunizationUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ImmunizationResponse:
    fields = body.model_dump(exclude_unset=True)
    if "status" in fields and fields["status"] is not None:
        fields["status"] = fields["status"].value
    try:
        imm = await update_immunization(session, immunization_id, patient_id, account.id, **fields)
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ImmunizationResponse.model_validate(imm)


@router.delete("/patients/{patient_id}/immunizations/{immunization_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    immunization_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_immunization(session, immunization_id, patient_id, account.id)
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get(
    "/patients/{patient_id}/immunizations/{immunization_id}/fhir",
)
async def get_fhir(
    patient_id: uuid.UUID,
    immunization_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        imm = await get_immunization(session, immunization_id, patient_id, account.id)
    except ImmunizationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if imm is None:
        raise HTTPException(status_code=404, detail="Immunization not found")
    return to_fhir(imm, patient_id)


@router.get("/epi-vaccines", response_model=list[EPIVaccineResponse])
async def get_epi_vaccines(
    _account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[EPIVaccineResponse]:
    vaccines = await list_epi_vaccines(session)
    return [EPIVaccineResponse.model_validate(v) for v in vaccines]
