import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

AllergyError = ClinicalResourceError


async def create_allergy(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Allergy:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    allergy = Allergy(
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(allergy)
    await session.flush()
    await log_event(
        session,
        "allergy_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} allergy_id={allergy.id}",
    )
    await session.commit()
    return allergy


async def list_allergies(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Allergy], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    base = select(Allergy).where(
        Allergy.patient_id == patient_id,
        Allergy.account_id == account_id,
        Allergy.is_active.is_(True),
    )
    count_q = (
        select(func.count())
        .select_from(Allergy)
        .where(
            Allergy.patient_id == patient_id,
            Allergy.account_id == account_id,
            Allergy.is_active.is_(True),
        )
    )
    query = base.order_by(Allergy.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_allergy(
    session: AsyncSession,
    allergy_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Allergy | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(Allergy).where(
            Allergy.id == allergy_id,
            Allergy.patient_id == patient_id,
            Allergy.account_id == account_id,
            Allergy.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_allergy(
    session: AsyncSession,
    allergy_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Allergy:
    allergy = await get_allergy(session, allergy_id, patient_id, account_id)
    if allergy is None:
        raise AllergyError("Allergy not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(allergy, key, value)

    await session.flush()
    await log_event(
        session,
        "allergy_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} allergy_id={allergy.id}",
    )
    await session.commit()
    return allergy


async def soft_delete_allergy(
    session: AsyncSession,
    allergy_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    allergy = await get_allergy(session, allergy_id, patient_id, account_id)
    if allergy is None:
        raise AllergyError("Allergy not found", status_code=404)

    allergy.is_active = False
    await session.flush()
    await log_event(
        session,
        "allergy_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} allergy_id={allergy.id}",
    )
    await session.commit()
