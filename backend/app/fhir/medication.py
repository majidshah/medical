"""FHIR R4 MedicationStatement mapping layer using fhir.resources for schema validation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.dosage import Dosage
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.period import Period
from fhir.resources.reference import Reference

if TYPE_CHECKING:
    from app.models.medication import Medication as MedicationModel


def to_fhir(medication: MedicationModel, patient_reference_id: uuid.UUID) -> dict:
    coding_list = []
    if medication.code:
        coding_list.append(
            Coding(
                system=medication.code_system,
                code=medication.code,
                display=medication.display_name,
            )
        )

    kwargs: dict = {
        "id": str(medication.id),
        "subject": Reference(reference=f"Patient/{patient_reference_id}"),
        "status": medication.status,
        "medication": CodeableReference(
            concept=CodeableConcept(text=medication.display_name, coding=coding_list or None)
        ),
    }

    if medication.start_date or medication.end_date:
        period_kwargs: dict = {}
        if medication.start_date:
            period_kwargs["start"] = medication.start_date.isoformat()
        if medication.end_date:
            period_kwargs["end"] = medication.end_date.isoformat()
        kwargs["effectivePeriod"] = Period(**period_kwargs)

    dosage_parts = []
    if medication.dosage:
        dosage_parts.append(medication.dosage)
    if medication.frequency:
        dosage_parts.append(medication.frequency)
    if medication.route:
        dosage_parts.append(medication.route)
    if dosage_parts:
        kwargs["dosage"] = [Dosage(text=", ".join(dosage_parts))]

    if medication.notes:
        kwargs["note"] = [{"text": medication.notes}]

    resource = MedicationStatement(**kwargs)
    return resource.dict(exclude_none=True)
