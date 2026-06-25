import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.services.audit import log_event

_DEPENDENT_ID_RE = re.compile(r"-D(\d+)$")


class PatientError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


async def create_patient(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    full_name: str,
    gender: str,
    relationship_to_account: str,
    date_of_birth=None,
    cnic: str | None = None,
    guardian_patient_id: uuid.UUID | None = None,
) -> Patient:
    if cnic and guardian_patient_id:
        raise PatientError("Supply either cnic or guardian_patient_id, not both", status_code=422)
    if not cnic and not guardian_patient_id:
        raise PatientError(
            "Supply either cnic (for CNIC holder) or guardian_patient_id (for dependent)",
            status_code=422,
        )

    if cnic:
        return await _create_cnic_patient(
            session,
            account_id=account_id,
            cnic=cnic,
            full_name=full_name,
            gender=gender,
            relationship_to_account=relationship_to_account,
            date_of_birth=date_of_birth,
        )
    else:
        return await _create_dependent_patient(
            session,
            account_id=account_id,
            guardian_patient_id=guardian_patient_id,  # type: ignore[arg-type]
            full_name=full_name,
            gender=gender,
            relationship_to_account=relationship_to_account,
            date_of_birth=date_of_birth,
        )


async def _create_cnic_patient(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    cnic: str,
    full_name: str,
    gender: str,
    relationship_to_account: str,
    date_of_birth,
) -> Patient:
    patient = Patient(
        account_id=account_id,
        medical_id=cnic,
        full_name=full_name,
        date_of_birth=date_of_birth,
        gender=gender,
        relationship_to_account=relationship_to_account,
        has_cnic=True,
        guardian_patient_id=None,
    )
    session.add(patient)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise PatientError("A patient with this CNIC already exists", status_code=409) from None

    await log_event(
        session, "patient_created", account_id=account_id, detail=f"patient_id={patient.id}"
    )
    await session.commit()
    return patient


async def _create_dependent_patient(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    guardian_patient_id: uuid.UUID,
    full_name: str,
    gender: str,
    relationship_to_account: str,
    date_of_birth,
) -> Patient:
    guardian = await get_patient_for_account(session, guardian_patient_id, account_id)
    if guardian is None:
        raise PatientError("Guardian patient not found", status_code=404)
    if not guardian.has_cnic:
        raise PatientError("Guardian must have a CNIC to add dependents", status_code=422)

    # Collision-safe dependent ID generation:
    # Lock the guardian row (SELECT ... FOR UPDATE) so concurrent inserts serialize.
    # Then compute next D-number from existing dependents. The DB unique constraint
    # on medical_id is the backstop if a race still occurs.
    locked = await session.execute(
        select(Patient).where(Patient.id == guardian.id).with_for_update()
    )
    locked.scalar_one()

    result = await session.execute(
        select(Patient.medical_id).where(
            Patient.guardian_patient_id == guardian.id,
            Patient.account_id == account_id,
        )
    )
    existing_ids = result.scalars().all()

    max_n = 0
    for mid in existing_ids:
        m = _DEPENDENT_ID_RE.search(mid)
        if m:
            max_n = max(max_n, int(m.group(1)))

    medical_id = f"{guardian.medical_id}-D{max_n + 1}"

    patient = Patient(
        account_id=account_id,
        medical_id=medical_id,
        full_name=full_name,
        date_of_birth=date_of_birth,
        gender=gender,
        relationship_to_account=relationship_to_account,
        has_cnic=False,
        guardian_patient_id=guardian.id,
    )
    session.add(patient)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise PatientError(
            "Failed to generate dependent ID — please retry", status_code=409
        ) from None

    await log_event(
        session, "patient_created", account_id=account_id, detail=f"patient_id={patient.id}"
    )
    await session.commit()
    return patient


async def list_patients(
    session: AsyncSession,
    account_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    include_inactive: bool = False,
) -> tuple[list[Patient], int]:
    query = select(Patient).where(Patient.account_id == account_id)
    count_query = select(func.count()).select_from(Patient).where(Patient.account_id == account_id)

    if not include_inactive:
        query = query.where(Patient.is_active.is_(True))
        count_query = count_query.where(Patient.is_active.is_(True))

    query = query.order_by(Patient.created_at).limit(limit).offset(offset)

    result = await session.execute(query)
    patients = list(result.scalars().all())
    total = (await session.execute(count_query)).scalar_one()
    return patients, total


async def get_patient(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Patient | None:
    return await get_patient_for_account(session, patient_id, account_id)


async def update_patient(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Patient:
    patient = await get_patient_for_account(session, patient_id, account_id)
    if patient is None:
        raise PatientError("Patient not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(patient, key, value)

    await session.flush()
    await log_event(
        session, "patient_updated", account_id=account_id, detail=f"patient_id={patient.id}"
    )
    await session.commit()
    return patient


async def soft_delete_patient(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Patient:
    patient = await get_patient_for_account(session, patient_id, account_id)
    if patient is None:
        raise PatientError("Patient not found", status_code=404)

    patient.is_active = False
    await session.flush()
    await log_event(
        session, "patient_deleted", account_id=account_id, detail=f"patient_id={patient.id}"
    )
    await session.commit()
    return patient


async def search_patient_by_medical_id(
    session: AsyncSession,
    account_id: uuid.UUID,
    medical_id: str,
) -> Patient | None:
    result = await session.execute(
        select(Patient).where(
            Patient.account_id == account_id,
            Patient.medical_id == medical_id,
            Patient.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_patient_for_account(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Patient | None:
    result = await session.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.account_id == account_id,
            Patient.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
