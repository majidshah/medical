import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.family_history import FamilyHistory
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

FamilyHistoryError = ClinicalResourceError


async def create_family_history(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> FamilyHistory:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    fh = FamilyHistory(
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(fh)
    await session.flush()
    await log_event(
        session,
        "family_history_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} family_history_id={fh.id}",
    )
    await session.commit()
    return fh


async def list_family_histories(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[FamilyHistory], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    base = select(FamilyHistory).where(
        FamilyHistory.patient_id == patient_id,
        FamilyHistory.account_id == account_id,
        FamilyHistory.is_active.is_(True),
    )
    count_q = (
        select(func.count())
        .select_from(FamilyHistory)
        .where(
            FamilyHistory.patient_id == patient_id,
            FamilyHistory.account_id == account_id,
            FamilyHistory.is_active.is_(True),
        )
    )
    query = base.order_by(FamilyHistory.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_family_history(
    session: AsyncSession,
    family_history_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> FamilyHistory | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(FamilyHistory).where(
            FamilyHistory.id == family_history_id,
            FamilyHistory.patient_id == patient_id,
            FamilyHistory.account_id == account_id,
            FamilyHistory.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_family_history(
    session: AsyncSession,
    family_history_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> FamilyHistory:
    fh = await get_family_history(session, family_history_id, patient_id, account_id)
    if fh is None:
        raise FamilyHistoryError("Family history not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(fh, key, value)

    await session.flush()
    await log_event(
        session,
        "family_history_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} family_history_id={fh.id}",
    )
    await session.commit()
    return fh


async def soft_delete_family_history(
    session: AsyncSession,
    family_history_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    fh = await get_family_history(session, family_history_id, patient_id, account_id)
    if fh is None:
        raise FamilyHistoryError("Family history not found", status_code=404)

    fh.is_active = False
    await session.flush()
    await log_event(
        session,
        "family_history_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} family_history_id={fh.id}",
    )
    await session.commit()
