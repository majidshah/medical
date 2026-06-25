"""FHIR R4 Condition mapping layer using fhir.resources for schema validation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.condition import Condition
from fhir.resources.reference import Reference

if TYPE_CHECKING:
    from app.models.condition import Condition as ConditionModel


def to_fhir(condition: ConditionModel, patient_reference_id: uuid.UUID) -> dict:
    coding_list = []
    if condition.code:
        coding_list.append(
            Coding(
                system=condition.code_system,
                code=condition.code,
                display=condition.display_name,
            )
        )

    kwargs: dict = {
        "id": str(condition.id),
        "subject": Reference(reference=f"Patient/{patient_reference_id}"),
        "clinicalStatus": CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                    code=condition.clinical_status,
                )
            ]
        ),
        "code": CodeableConcept(text=condition.display_name, coding=coding_list or None),
    }

    if condition.onset_date:
        kwargs["onsetDateTime"] = condition.onset_date.isoformat()

    if condition.abatement_date:
        kwargs["abatementDateTime"] = condition.abatement_date.isoformat()

    if condition.notes:
        kwargs["note"] = [{"text": condition.notes}]

    resource = Condition(**kwargs)
    return resource.dict(exclude_none=True)
