"""FHIR R4 Immunization mapping layer using fhir.resources for schema validation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.immunization import Immunization
from fhir.resources.reference import Reference

if TYPE_CHECKING:
    from app.models.immunization import Immunization as ImmunizationModel


def to_fhir(imm: ImmunizationModel, patient_reference_id: uuid.UUID) -> dict:
    coding_list = []
    if imm.code:
        coding_list.append(
            Coding(system=imm.code_system, code=imm.code, display=imm.vaccine_display_name)
        )

    kwargs: dict = {
        "id": str(imm.id),
        "patient": Reference(reference=f"Patient/{patient_reference_id}"),
        "status": imm.status,
        "vaccineCode": CodeableConcept(text=imm.vaccine_display_name, coding=coding_list or None),
        "occurrenceDateTime": imm.occurrence_date.isoformat(),
    }

    if imm.lot_number:
        kwargs["lotNumber"] = imm.lot_number

    if imm.manufacturer:
        kwargs["manufacturer"] = CodeableReference(concept=CodeableConcept(text=imm.manufacturer))

    if imm.site:
        kwargs["site"] = CodeableConcept(text=imm.site)

    if imm.dose_number is not None:
        kwargs["protocolApplied"] = [{"doseNumber": str(imm.dose_number)}]

    if imm.notes:
        kwargs["note"] = [{"text": imm.notes}]

    resource = Immunization(**kwargs)
    return resource.dict(exclude_none=True)
