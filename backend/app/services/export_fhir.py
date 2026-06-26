"""FHIR R4 Bundle export — assembles all active clinical resources for a patient."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fhir.allergy import to_fhir as allergy_to_fhir
from app.fhir.condition import to_fhir as condition_to_fhir
from app.fhir.family_history import to_fhir as family_history_to_fhir
from app.fhir.immunization import to_fhir as immunization_to_fhir
from app.fhir.medication import to_fhir as medication_to_fhir
from app.fhir.observation import to_fhir as observation_to_fhir
from app.models.allergy import Allergy
from app.models.condition import Condition
from app.models.family_history import FamilyHistory
from app.models.immunization import Immunization
from app.models.lab_result import LabResult
from app.models.lifestyle_observation import LifestyleObservation
from app.models.medication import Medication
from app.models.observation_type import ObservationType
from app.services.patient import get_patient_for_account


async def build_fhir_bundle(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> dict | None:
    patient = await get_patient_for_account(session, patient_id, account_id)
    if patient is None:
        return None

    patient_ref = str(patient.id)
    entries = []

    patient_resource = {
        "resourceType": "Patient",
        "id": patient_ref,
        "name": [{"text": patient.full_name}],
        "gender": patient.gender,
        "identifier": [{"value": patient.medical_id}],
    }
    if patient.date_of_birth:
        patient_resource["birthDate"] = patient.date_of_birth.isoformat()
    entries.append(_entry(patient_resource))

    conditions = await session.execute(
        select(Condition).where(
            Condition.patient_id == patient_id,
            Condition.account_id == account_id,
            Condition.is_active.is_(True),
        )
    )
    for c in conditions.scalars().all():
        entries.append(_entry(condition_to_fhir(c, patient.id)))

    allergies = await session.execute(
        select(Allergy).where(
            Allergy.patient_id == patient_id,
            Allergy.account_id == account_id,
            Allergy.is_active.is_(True),
        )
    )
    for a in allergies.scalars().all():
        entries.append(_entry(allergy_to_fhir(a, patient.id)))

    medications = await session.execute(
        select(Medication).where(
            Medication.patient_id == patient_id,
            Medication.account_id == account_id,
            Medication.is_active.is_(True),
        )
    )
    for m in medications.scalars().all():
        entries.append(_entry(medication_to_fhir(m, patient.id)))

    immunizations = await session.execute(
        select(Immunization).where(
            Immunization.patient_id == patient_id,
            Immunization.account_id == account_id,
            Immunization.is_active.is_(True),
        )
    )
    for i in immunizations.scalars().all():
        entries.append(_entry(immunization_to_fhir(i, patient.id)))

    family_histories = await session.execute(
        select(FamilyHistory).where(
            FamilyHistory.patient_id == patient_id,
            FamilyHistory.account_id == account_id,
            FamilyHistory.is_active.is_(True),
        )
    )
    for fh in family_histories.scalars().all():
        entries.append(_entry(family_history_to_fhir(fh, patient.id)))

    obs_results = await session.execute(
        select(LifestyleObservation).where(
            LifestyleObservation.patient_id == patient_id,
            LifestyleObservation.account_id == account_id,
            LifestyleObservation.is_active.is_(True),
        )
    )
    obs_type_cache: dict[uuid.UUID, ObservationType] = {}
    for o in obs_results.scalars().all():
        if o.observation_type_id not in obs_type_cache:
            t = await session.execute(
                select(ObservationType).where(ObservationType.id == o.observation_type_id)
            )
            obs_type_cache[o.observation_type_id] = t.scalar_one()
        ot = obs_type_cache[o.observation_type_id]
        entries.append(
            _entry(
                observation_to_fhir(
                    observation_id=o.id,
                    patient_reference_id=patient.id,
                    loinc_code=ot.loinc_code,
                    display_label=ot.display_label,
                    effective_date=o.effective_date.isoformat(),
                    value_numeric=float(o.value_numeric) if o.value_numeric is not None else None,
                    value_code=o.value_code,
                    value_text=o.value_text,
                    unit=o.unit,
                    category_code="social-history",
                    category_display="Social History",
                )
            )
        )

    lab_results = await session.execute(
        select(LabResult).where(
            LabResult.patient_id == patient_id,
            LabResult.account_id == account_id,
            LabResult.is_active.is_(True),
        )
    )
    for lr in lab_results.scalars().all():
        entries.append(
            _entry(
                observation_to_fhir(
                    observation_id=lr.id,
                    patient_reference_id=patient.id,
                    loinc_code=lr.loinc_code,
                    display_label=lr.display_name,
                    effective_date=lr.effective_date.isoformat(),
                    value_numeric=(
                        float(lr.value_numeric) if lr.value_numeric is not None else None
                    ),
                    value_text=lr.value_text,
                    unit=lr.unit,
                    category_code="laboratory",
                    category_display="Laboratory",
                )
            )
        )

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries,
    }


def _entry(resource: dict) -> dict:
    rid = resource.get("id", str(uuid.uuid4()))
    return {
        "fullUrl": f"urn:uuid:{rid}",
        "resource": resource,
    }
