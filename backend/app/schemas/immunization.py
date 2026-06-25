import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class ImmunizationStatus(StrEnum):
    completed = "completed"
    entered_in_error = "entered-in-error"
    not_done = "not-done"


class ImmunizationCreate(BaseModel):
    vaccine_display_name: str = Field(min_length=1, max_length=500)
    epi_vaccine_id: uuid.UUID | None = None
    code: str | None = None
    code_system: str | None = None
    dose_number: int | None = None
    occurrence_date: date
    lot_number: str | None = None
    manufacturer: str | None = None
    site: str | None = None
    status: ImmunizationStatus = ImmunizationStatus.completed
    notes: str | None = None


class ImmunizationUpdate(BaseModel):
    vaccine_display_name: str | None = Field(default=None, min_length=1, max_length=500)
    code: str | None = None
    code_system: str | None = None
    dose_number: int | None = None
    occurrence_date: date | None = None
    lot_number: str | None = None
    manufacturer: str | None = None
    site: str | None = None
    status: ImmunizationStatus | None = None
    notes: str | None = None


class ImmunizationResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    epi_vaccine_id: uuid.UUID | None
    vaccine_display_name: str
    code_system: str | None
    code: str | None
    dose_number: int | None
    occurrence_date: date
    lot_number: str | None
    manufacturer: str | None
    site: str | None
    status: str
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ImmunizationListResponse(BaseModel):
    items: list[ImmunizationResponse]
    total: int
    limit: int
    offset: int


class EPIVaccineResponse(BaseModel):
    id: uuid.UUID
    name: str
    short_name: str
    total_doses: int | None
    description: str | None

    model_config = {"from_attributes": True}
