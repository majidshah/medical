import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

MedicationError = ClinicalResourceError


async def create_medication(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Medication:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    medication = Medication(
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(medication)
    await session.flush()
    await log_event(
        session,
        "medication_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} medication_id={medication.id}",
    )
    await session.commit()
    return medication


async def list_medications(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Medication], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    base = select(Medication).where(
        Medication.patient_id == patient_id,
        Medication.account_id == account_id,
        Medication.is_active.is_(True),
    )
    count_q = (
        select(func.count())
        .select_from(Medication)
        .where(
            Medication.patient_id == patient_id,
            Medication.account_id == account_id,
            Medication.is_active.is_(True),
        )
    )
    query = base.order_by(Medication.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_medication(
    session: AsyncSession,
    medication_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Medication | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(Medication).where(
            Medication.id == medication_id,
            Medication.patient_id == patient_id,
            Medication.account_id == account_id,
            Medication.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_medication(
    session: AsyncSession,
    medication_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Medication:
    medication = await get_medication(session, medication_id, patient_id, account_id)
    if medication is None:
        raise MedicationError("Medication not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(medication, key, value)

    await session.flush()
    await log_event(
        session,
        "medication_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} medication_id={medication.id}",
    )
    await session.commit()
    return medication


async def soft_delete_medication(
    session: AsyncSession,
    medication_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    medication = await get_medication(session, medication_id, patient_id, account_id)
    if medication is None:
        raise MedicationError("Medication not found", status_code=404)

    medication.is_active = False
    await session.flush()
    await log_event(
        session,
        "medication_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} medication_id={medication.id}",
    )
    await session.commit()
