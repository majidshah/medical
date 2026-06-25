import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.epi_vaccine import EPIVaccine
from app.models.immunization import Immunization
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

ImmunizationError = ClinicalResourceError


async def create_immunization(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Immunization:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    epi_id = fields.get("epi_vaccine_id")
    if epi_id:
        result = await session.execute(select(EPIVaccine).where(EPIVaccine.id == epi_id))
        if result.scalar_one_or_none() is None:
            raise ImmunizationError("EPI vaccine not found", status_code=404)

    imm = Immunization(
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(imm)
    await session.flush()
    await log_event(
        session,
        "immunization_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} immunization_id={imm.id}",
    )
    await session.commit()
    return imm


async def list_immunizations(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Immunization], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    base = select(Immunization).where(
        Immunization.patient_id == patient_id,
        Immunization.account_id == account_id,
        Immunization.is_active.is_(True),
    )
    count_q = (
        select(func.count())
        .select_from(Immunization)
        .where(
            Immunization.patient_id == patient_id,
            Immunization.account_id == account_id,
            Immunization.is_active.is_(True),
        )
    )
    query = base.order_by(Immunization.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_immunization(
    session: AsyncSession,
    immunization_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Immunization | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(Immunization).where(
            Immunization.id == immunization_id,
            Immunization.patient_id == patient_id,
            Immunization.account_id == account_id,
            Immunization.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_immunization(
    session: AsyncSession,
    immunization_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Immunization:
    imm = await get_immunization(session, immunization_id, patient_id, account_id)
    if imm is None:
        raise ImmunizationError("Immunization not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(imm, key, value)

    await session.flush()
    await log_event(
        session,
        "immunization_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} immunization_id={imm.id}",
    )
    await session.commit()
    return imm


async def soft_delete_immunization(
    session: AsyncSession,
    immunization_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    imm = await get_immunization(session, immunization_id, patient_id, account_id)
    if imm is None:
        raise ImmunizationError("Immunization not found", status_code=404)

    imm.is_active = False
    await session.flush()
    await log_event(
        session,
        "immunization_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} immunization_id={imm.id}",
    )
    await session.commit()


async def list_epi_vaccines(session: AsyncSession) -> list[EPIVaccine]:
    result = await session.execute(select(EPIVaccine).order_by(EPIVaccine.name))
    return list(result.scalars().all())
