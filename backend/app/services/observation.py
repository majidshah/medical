import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lifestyle_observation import LifestyleObservation
from app.models.observation_type import ObservationType
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

ObservationError = ClinicalResourceError


async def _get_obs_type(session: AsyncSession, type_id: uuid.UUID) -> ObservationType:
    result = await session.execute(
        select(ObservationType).where(
            ObservationType.id == type_id, ObservationType.is_active.is_(True)
        )
    )
    obs_type = result.scalar_one_or_none()
    if obs_type is None:
        raise ObservationError("Observation type not found", status_code=404)
    return obs_type


async def _validate_value(
    obs_type: ObservationType,
    value_numeric: float | None,
    value_code: str | None,
    value_text: str | None,
) -> None:
    vt = obs_type.value_type
    if vt == "numeric" and value_numeric is None:
        raise ObservationError(
            f"Observation type '{obs_type.key}' requires value_numeric", status_code=422
        )
    if vt == "coded" and value_code is None:
        raise ObservationError(
            f"Observation type '{obs_type.key}' requires value_code", status_code=422
        )
    if vt == "text" and value_text is None:
        raise ObservationError(
            f"Observation type '{obs_type.key}' requires value_text", status_code=422
        )


async def create_observation(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    observation_type_id: uuid.UUID,
    effective_date: date,
    value_numeric: float | None = None,
    value_code: str | None = None,
    value_text: str | None = None,
    unit: str | None = None,
    notes: str | None = None,
) -> LifestyleObservation:
    patient = await resolve_patient_or_404(session, patient_id, account_id)
    obs_type = await _get_obs_type(session, observation_type_id)
    await _validate_value(obs_type, value_numeric, value_code, value_text)

    if unit is None:
        unit = obs_type.unit

    obs = LifestyleObservation(
        patient_id=patient.id,
        account_id=patient.account_id,
        observation_type_id=observation_type_id,
        effective_date=effective_date,
        value_numeric=value_numeric,
        value_code=value_code,
        value_text=value_text,
        unit=unit,
        notes=notes,
    )
    session.add(obs)
    await session.flush()
    await log_event(
        session,
        "observation_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} observation_id={obs.id} type={obs_type.key}",
    )
    await session.commit()
    return obs


async def list_observations(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    type_key: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[LifestyleObservation], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    filters = [
        LifestyleObservation.patient_id == patient_id,
        LifestyleObservation.account_id == account_id,
        LifestyleObservation.is_active.is_(True),
    ]

    if type_key:
        type_result = await session.execute(
            select(ObservationType.id).where(ObservationType.key == type_key)
        )
        type_id = type_result.scalar_one_or_none()
        if type_id is None:
            return [], 0
        filters.append(LifestyleObservation.observation_type_id == type_id)

    if from_date:
        filters.append(LifestyleObservation.effective_date >= from_date)
    if to_date:
        filters.append(LifestyleObservation.effective_date <= to_date)

    base = select(LifestyleObservation).where(*filters)
    count_q = select(func.count()).select_from(LifestyleObservation).where(*filters)
    query = base.order_by(LifestyleObservation.effective_date.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_observation(
    session: AsyncSession,
    observation_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> LifestyleObservation | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(LifestyleObservation).where(
            LifestyleObservation.id == observation_id,
            LifestyleObservation.patient_id == patient_id,
            LifestyleObservation.account_id == account_id,
            LifestyleObservation.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_observation(
    session: AsyncSession,
    observation_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> LifestyleObservation:
    obs = await get_observation(session, observation_id, patient_id, account_id)
    if obs is None:
        raise ObservationError("Observation not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(obs, key, value)

    await session.flush()
    await log_event(
        session,
        "observation_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} observation_id={obs.id}",
    )
    await session.commit()
    return obs


async def soft_delete_observation(
    session: AsyncSession,
    observation_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    obs = await get_observation(session, observation_id, patient_id, account_id)
    if obs is None:
        raise ObservationError("Observation not found", status_code=404)

    obs.is_active = False
    await session.flush()
    await log_event(
        session,
        "observation_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} observation_id={obs.id}",
    )
    await session.commit()


async def get_trend(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    type_key: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[ObservationType | None, list[LifestyleObservation]]:
    await resolve_patient_or_404(session, patient_id, account_id)

    type_result = await session.execute(
        select(ObservationType).where(ObservationType.key == type_key)
    )
    obs_type = type_result.scalar_one_or_none()
    if obs_type is None:
        raise ObservationError("Observation type not found", status_code=404)

    filters = [
        LifestyleObservation.patient_id == patient_id,
        LifestyleObservation.account_id == account_id,
        LifestyleObservation.observation_type_id == obs_type.id,
        LifestyleObservation.is_active.is_(True),
    ]
    if from_date:
        filters.append(LifestyleObservation.effective_date >= from_date)
    if to_date:
        filters.append(LifestyleObservation.effective_date <= to_date)

    query = (
        select(LifestyleObservation)
        .where(*filters)
        .order_by(LifestyleObservation.effective_date.asc())
    )
    result = await session.execute(query)
    return obs_type, list(result.scalars().all())


async def list_observation_types(session: AsyncSession) -> list[ObservationType]:
    result = await session.execute(
        select(ObservationType)
        .where(ObservationType.is_active.is_(True))
        .order_by(ObservationType.display_label)
    )
    return list(result.scalars().all())
