"""FHIR R4 FamilyMemberHistory mapping layer using fhir.resources for schema validation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fhir.resources.age import Age
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.familymemberhistory import FamilyMemberHistory
from fhir.resources.reference import Reference

if TYPE_CHECKING:
    from app.models.family_history import FamilyHistory as FamilyHistoryModel

_RELATIONSHIP_CODING = {
    "mother": ("MTH", "mother"),
    "father": ("FTH", "father"),
    "brother": ("BRO", "brother"),
    "sister": ("SIS", "sister"),
    "grandfather-paternal": ("PGRFTH", "paternal grandfather"),
    "grandmother-paternal": ("PGRMTH", "paternal grandmother"),
    "grandfather-maternal": ("MGRFTH", "maternal grandfather"),
    "grandmother-maternal": ("MGRMTH", "maternal grandmother"),
    "son": ("SONC", "son"),
    "daughter": ("DAUC", "daughter"),
    "other": ("FAMMEMB", "family member"),
}


def to_fhir(fh: FamilyHistoryModel, patient_reference_id: uuid.UUID) -> dict:
    rel_code, rel_display = _RELATIONSHIP_CODING.get(fh.relationship, ("FAMMEMB", "family member"))

    coding_list = []
    if fh.condition_code:
        coding_list.append(
            Coding(
                system=fh.condition_code_system,
                code=fh.condition_code,
                display=fh.condition_display_name,
            )
        )

    condition_entry: dict = {
        "code": CodeableConcept(text=fh.condition_display_name, coding=coding_list or None),
    }

    if fh.onset_age is not None:
        condition_entry["onsetAge"] = Age(
            value=fh.onset_age, unit="years", system="http://unitsofmeasure.org", code="a"
        )

    kwargs: dict = {
        "id": str(fh.id),
        "patient": Reference(reference=f"Patient/{patient_reference_id}"),
        "status": "completed",
        "relationship": CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    code=rel_code,
                    display=rel_display,
                )
            ]
        ),
        "condition": [condition_entry],
    }

    if fh.deceased is not None:
        kwargs["deceasedBoolean"] = fh.deceased

    if fh.notes:
        kwargs["note"] = [{"text": fh.notes}]

    resource = FamilyMemberHistory(**kwargs)
    return resource.dict(exclude_none=True)
