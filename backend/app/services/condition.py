import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.condition import Condition
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

ConditionError = ClinicalResourceError


async def create_condition(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Condition:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    condition = Condition(
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(condition)
    await session.flush()
    await log_event(
        session,
        "condition_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} condition_id={condition.id}",
    )
    await session.commit()
    return condition


async def list_conditions(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Condition], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    base = select(Condition).where(
        Condition.patient_id == patient_id,
        Condition.account_id == account_id,
        Condition.is_active.is_(True),
    )
    count_q = (
        select(func.count())
        .select_from(Condition)
        .where(
            Condition.patient_id == patient_id,
            Condition.account_id == account_id,
            Condition.is_active.is_(True),
        )
    )
    query = base.order_by(Condition.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_condition(
    session: AsyncSession,
    condition_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Condition | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(Condition).where(
            Condition.id == condition_id,
            Condition.patient_id == patient_id,
            Condition.account_id == account_id,
            Condition.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_condition(
    session: AsyncSession,
    condition_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Condition:
    condition = await get_condition(session, condition_id, patient_id, account_id)
    if condition is None:
        raise ConditionError("Condition not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(condition, key, value)

    await session.flush()
    await log_event(
        session,
        "condition_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} condition_id={condition.id}",
    )
    await session.commit()
    return condition


async def soft_delete_condition(
    session: AsyncSession,
    condition_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    condition = await get_condition(session, condition_id, patient_id, account_id)
    if condition is None:
        raise ConditionError("Condition not found", status_code=404)

    condition.is_active = False
    await session.flush()
    await log_event(
        session,
        "condition_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} condition_id={condition.id}",
    )
    await session.commit()
