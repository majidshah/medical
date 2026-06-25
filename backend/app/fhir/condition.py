"""FHIR R4 Condition mapping layer.

Maps between the conditions ORM model and a FHIR R4 Condition resource.
All FHIR construction is centralised here — routers and services must not
build FHIR dicts inline. Other clinical resources should follow this pattern.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.condition import Condition as ConditionModel


def to_fhir(condition: ConditionModel, patient_reference_id: uuid.UUID) -> dict:
    resource: dict = {
        "resourceType": "Condition",
        "id": str(condition.id),
        "subject": {"reference": f"Patient/{patient_reference_id}"},
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": condition.clinical_status,
                }
            ]
        },
        "code": _build_code(condition),
    }

    if condition.onset_date:
        resource["onsetDateTime"] = condition.onset_date.isoformat()

    if condition.abatement_date:
        resource["abatementDateTime"] = condition.abatement_date.isoformat()

    if condition.notes:
        resource["note"] = [{"text": condition.notes}]

    return resource


def _build_code(condition: ConditionModel) -> dict:
    result: dict = {"text": condition.display_name}
    if condition.code:
        result["coding"] = [
            {
                "system": condition.code_system,
                "code": condition.code,
                "display": condition.display_name,
            }
        ]
    return result
