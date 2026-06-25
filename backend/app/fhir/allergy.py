"""FHIR R4 AllergyIntolerance mapping layer using fhir.resources for schema validation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference

if TYPE_CHECKING:
    from app.models.allergy import Allergy as AllergyModel


def to_fhir(allergy: AllergyModel, patient_reference_id: uuid.UUID) -> dict:
    coding_list = []
    if allergy.code:
        coding_list.append(
            Coding(
                system=allergy.code_system,
                code=allergy.code,
                display=allergy.display_name,
            )
        )

    kwargs: dict = {
        "id": str(allergy.id),
        "patient": Reference(reference=f"Patient/{patient_reference_id}"),
        "clinicalStatus": CodeableConcept(
            coding=[
                Coding(
                    system="http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    code=allergy.clinical_status,
                )
            ]
        ),
        "code": CodeableConcept(text=allergy.display_name, coding=coding_list or None),
        "category": [allergy.category],
    }

    if allergy.criticality:
        kwargs["criticality"] = allergy.criticality

    if allergy.onset_date:
        kwargs["onsetDateTime"] = allergy.onset_date.isoformat()

    if allergy.reaction:
        kwargs["reaction"] = [
            {
                "manifestation": [
                    CodeableReference(concept=CodeableConcept(text=allergy.reaction))
                ],
                "severity": allergy.severity,
            }
        ]
    elif allergy.severity:
        kwargs["reaction"] = [
            {
                "manifestation": [CodeableReference(concept=CodeableConcept(text="Unknown"))],
                "severity": allergy.severity,
            }
        ]

    if allergy.notes:
        kwargs["note"] = [{"text": allergy.notes}]

    resource = AllergyIntolerance(**kwargs)
    return resource.dict(exclude_none=True)
