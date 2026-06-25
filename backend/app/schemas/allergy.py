import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class AllergyCategory(StrEnum):
    food = "food"
    medication = "medication"
    environment = "environment"
    biologic = "biologic"


class AllergyCriticality(StrEnum):
    low = "low"
    high = "high"
    unable_to_assess = "unable-to-assess"


class AllergyClinicalStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    resolved = "resolved"


class AllergySeverity(StrEnum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class AllergyCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=500)
    code: str | None = None
    code_system: str = "http://snomed.info/sct"
    category: AllergyCategory
    criticality: AllergyCriticality | None = None
    clinical_status: AllergyClinicalStatus = AllergyClinicalStatus.active
    reaction: str | None = None
    severity: AllergySeverity | None = None
    onset_date: date | None = None
    notes: str | None = None


class AllergyUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=500)
    code: str | None = None
    code_system: str | None = None
    category: AllergyCategory | None = None
    criticality: AllergyCriticality | None = None
    clinical_status: AllergyClinicalStatus | None = None
    reaction: str | None = None
    severity: AllergySeverity | None = None
    onset_date: date | None = None
    notes: str | None = None


class AllergyResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    code_system: str
    code: str | None
    display_name: str
    category: str
    criticality: str | None
    clinical_status: str
    reaction: str | None
    severity: str | None
    onset_date: date | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class AllergyListResponse(BaseModel):
    items: list[AllergyResponse]
    total: int
    limit: int
    offset: int
