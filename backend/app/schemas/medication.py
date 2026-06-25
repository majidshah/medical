import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class MedicationStatus(StrEnum):
    active = "active"
    completed = "completed"
    stopped = "stopped"
    on_hold = "on-hold"
    unknown = "unknown"


class MedicationCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=500)
    code: str | None = None
    code_system: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus = MedicationStatus.active
    start_date: date | None = None
    end_date: date | None = None
    prescribed_by: str | None = None
    notes: str | None = None


class MedicationUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=500)
    code: str | None = None
    code_system: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    prescribed_by: str | None = None
    notes: str | None = None


class MedicationResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    code_system: str | None
    code: str | None
    display_name: str
    dosage: str | None
    frequency: str | None
    route: str | None
    status: str
    start_date: date | None
    end_date: date | None
    prescribed_by: str | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class MedicationListResponse(BaseModel):
    items: list[MedicationResponse]
    total: int
    limit: int
    offset: int
