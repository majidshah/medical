import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class ClinicalStatus(StrEnum):
    active = "active"
    recurrence = "recurrence"
    relapse = "relapse"
    inactive = "inactive"
    remission = "remission"
    resolved = "resolved"


class ConditionCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=500)
    code: str | None = None
    code_system: str = "http://snomed.info/sct"
    clinical_status: ClinicalStatus = ClinicalStatus.active
    onset_date: date | None = None
    abatement_date: date | None = None
    notes: str | None = None


class ConditionUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=500)
    code: str | None = None
    code_system: str | None = None
    clinical_status: ClinicalStatus | None = None
    onset_date: date | None = None
    abatement_date: date | None = None
    notes: str | None = None


class ConditionResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    code_system: str
    code: str | None
    display_name: str
    clinical_status: str
    onset_date: date | None
    abatement_date: date | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ConditionListResponse(BaseModel):
    items: list[ConditionResponse]
    total: int
    limit: int
    offset: int
