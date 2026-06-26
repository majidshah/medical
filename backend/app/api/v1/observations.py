import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.observation import to_fhir
from app.models.account import Account
from app.schemas.observation import (
    ObservationCreate,
    ObservationListResponse,
    ObservationResponse,
    ObservationTypeResponse,
    ObservationUpdate,
    TrendPoint,
    TrendResponse,
)
from app.services.observation import (
    ObservationError,
    create_observation,
    get_observation,
    get_trend,
    list_observation_types,
    list_observations,
    soft_delete_observation,
    update_observation,
)

router = APIRouter(tags=["observations"])


@router.post(
    "/patients/{patient_id}/observations",
    response_model=ObservationResponse,
    status_code=201,
)
async def create(
    patient_id: uuid.UUID,
    body: ObservationCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationResponse:
    try:
        obs = await create_observation(
            session,
            patient_id,
            account.id,
            observation_type_id=body.observation_type_id,
            effective_date=body.effective_date,
            value_numeric=body.value_numeric,
            value_code=body.value_code,
            value_text=body.value_text,
            unit=body.unit,
            notes=body.notes,
        )
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ObservationResponse.model_validate(obs)


@router.get(
    "/patients/{patient_id}/observations",
    response_model=ObservationListResponse,
)
async def list_all(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    type: str | None = Query(default=None, alias="type"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ObservationListResponse:
    try:
        items, total = await list_observations(
            session,
            patient_id,
            account.id,
            type_key=type,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ObservationListResponse(
        items=[ObservationResponse.model_validate(o) for o in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/patients/{patient_id}/observations/trend",
    response_model=TrendResponse,
)
async def trend(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    type: str = Query(alias="type"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> TrendResponse:
    try:
        obs_type, observations = await get_trend(
            session, patient_id, account.id, type, from_date, to_date
        )
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    chartable = obs_type.value_type == "numeric"
    points = []
    for o in observations:
        value: float | str | None = None
        if o.value_numeric is not None:
            value = float(o.value_numeric)
        elif o.value_code is not None:
            value = o.value_code
        elif o.value_text is not None:
            value = o.value_text
        points.append(TrendPoint(effective_date=o.effective_date, value=value, unit=o.unit))

    return TrendResponse(observation_type_key=obs_type.key, chartable=chartable, points=points)


@router.get(
    "/patients/{patient_id}/observations/{observation_id}",
    response_model=ObservationResponse,
)
async def get_one(
    patient_id: uuid.UUID,
    observation_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationResponse:
    try:
        obs = await get_observation(session, observation_id, patient_id, account.id)
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if obs is None:
        raise HTTPException(status_code=404, detail="Observation not found")
    return ObservationResponse.model_validate(obs)


@router.patch(
    "/patients/{patient_id}/observations/{observation_id}",
    response_model=ObservationResponse,
)
async def patch(
    patient_id: uuid.UUID,
    observation_id: uuid.UUID,
    body: ObservationUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ObservationResponse:
    fields = body.model_dump(exclude_unset=True)
    try:
        obs = await update_observation(session, observation_id, patient_id, account.id, **fields)
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ObservationResponse.model_validate(obs)


@router.delete(
    "/patients/{patient_id}/observations/{observation_id}",
    status_code=204,
)
async def delete(
    patient_id: uuid.UUID,
    observation_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_observation(session, observation_id, patient_id, account.id)
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/patients/{patient_id}/observations/{observation_id}/fhir")
async def get_fhir(
    patient_id: uuid.UUID,
    observation_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        obs = await get_observation(session, observation_id, patient_id, account.id)
    except ObservationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if obs is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    from sqlalchemy import select as sa_select

    from app.models.observation_type import ObservationType

    type_result = await session.execute(
        sa_select(ObservationType).where(ObservationType.id == obs.observation_type_id)
    )
    obs_type = type_result.scalar_one()

    return to_fhir(
        observation_id=obs.id,
        patient_reference_id=patient_id,
        loinc_code=obs_type.loinc_code,
        display_label=obs_type.display_label,
        effective_date=obs.effective_date.isoformat(),
        value_numeric=float(obs.value_numeric) if obs.value_numeric is not None else None,
        value_code=obs.value_code,
        value_text=obs.value_text,
        unit=obs.unit,
        notes=obs.notes,
    )


@router.get("/observation-types", response_model=list[ObservationTypeResponse])
async def get_observation_types_list(
    _account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ObservationTypeResponse]:
    types = await list_observation_types(session)
    return [ObservationTypeResponse.model_validate(t) for t in types]
