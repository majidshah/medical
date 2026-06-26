import uuid
from datetime import date

from pydantic import BaseModel, model_validator


class ObservationCreate(BaseModel):
    observation_type_id: uuid.UUID
    effective_date: date
    value_numeric: float | None = None
    value_code: str | None = None
    value_text: str | None = None
    unit: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def exactly_one_value(self):
        set_count = sum(
            v is not None for v in [self.value_numeric, self.value_code, self.value_text]
        )
        if set_count != 1:
            raise ValueError("Exactly one of value_numeric, value_code, or value_text must be set")
        return self


class ObservationUpdate(BaseModel):
    effective_date: date | None = None
    value_numeric: float | None = None
    value_code: str | None = None
    value_text: str | None = None
    unit: str | None = None
    notes: str | None = None


class ObservationResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    observation_type_id: uuid.UUID
    effective_date: date
    value_numeric: float | None
    value_code: str | None
    value_text: str | None
    unit: str | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ObservationListResponse(BaseModel):
    items: list[ObservationResponse]
    total: int
    limit: int
    offset: int


class TrendPoint(BaseModel):
    effective_date: date
    value: float | str | None
    unit: str | None


class TrendResponse(BaseModel):
    observation_type_key: str
    chartable: bool
    points: list[TrendPoint]


class ObservationTypeResponse(BaseModel):
    id: uuid.UUID
    key: str
    display_label: str
    loinc_code: str | None
    value_type: str
    unit: str | None

    model_config = {"from_attributes": True}
