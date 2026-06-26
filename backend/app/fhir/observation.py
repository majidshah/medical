"""FHIR R4 Observation mapping layer using fhir.resources for schema validation.

Designed for reuse across lifestyle observations (this slice) and lab results
(slice 8). The to_fhir function accepts generic observation data — it is not
hardcoded to lifestyle-only assumptions.
"""

from __future__ import annotations

import uuid
from typing import Any

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.observation import Observation
from fhir.resources.quantity import Quantity
from fhir.resources.reference import Reference


def to_fhir(
    *,
    observation_id: uuid.UUID,
    patient_reference_id: uuid.UUID,
    loinc_code: str | None,
    display_label: str,
    effective_date: str,
    value_numeric: float | None = None,
    value_code: str | None = None,
    value_text: str | None = None,
    unit: str | None = None,
    notes: str | None = None,
    status: str = "final",
    category_code: str = "social-history",
    category_display: str = "Social History",
) -> dict:
    coding_list = []
    if loinc_code:
        coding_list.append(
            Coding(system="http://loinc.org", code=loinc_code, display=display_label)
        )

    kwargs: dict[str, Any] = {
        "id": str(observation_id),
        "status": status,
        "subject": Reference(reference=f"Patient/{patient_reference_id}"),
        "code": CodeableConcept(text=display_label, coding=coding_list or None),
        "effectiveDateTime": effective_date,
        "category": [
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/observation-category",
                        code=category_code,
                        display=category_display,
                    )
                ]
            )
        ],
    }

    if value_numeric is not None:
        q_kwargs: dict[str, Any] = {"value": value_numeric}
        if unit:
            q_kwargs["unit"] = unit
        kwargs["valueQuantity"] = Quantity(**q_kwargs)
    elif value_code is not None:
        kwargs["valueCodeableConcept"] = CodeableConcept(text=value_code)
    elif value_text is not None:
        kwargs["valueString"] = value_text

    if notes:
        kwargs["note"] = [{"text": notes}]

    resource = Observation(**kwargs)
    return resource.dict(exclude_none=True)
