import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ReportCategory(StrEnum):
    lab = "lab"
    imaging = "imaging"


class ReportCreate(BaseModel):
    category: ReportCategory
    report_date: date
    lab_name: str | None = None
    file_id: uuid.UUID | None = None
    notes: str | None = None


class ReportUpdate(BaseModel):
    category: ReportCategory | None = None
    report_date: date | None = None
    lab_name: str | None = None
    file_id: uuid.UUID | None = None
    notes: str | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    category: str
    report_date: date
    lab_name: str | None
    file_id: uuid.UUID | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    limit: int
    offset: int


class ResultCreate(BaseModel):
    test_id: uuid.UUID | None = None
    display_name: str = Field(min_length=1, max_length=500)
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    effective_date: date
    notes: str | None = None

    @model_validator(mode="after")
    def exactly_one_value(self):
        set_count = sum(v is not None for v in [self.value_numeric, self.value_text])
        if set_count != 1:
            raise ValueError("Exactly one of value_numeric or value_text must be set")
        return self


class ResultUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=500)
    value_numeric: float | None = None
    value_text: str | None = None
    unit: str | None = None
    effective_date: date | None = None
    notes: str | None = None


class ResultResponse(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    test_id: uuid.UUID | None
    display_name: str
    loinc_code: str | None
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    effective_date: date
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ResultListResponse(BaseModel):
    items: list[ResultResponse]
    total: int
    limit: int
    offset: int


class StoredFileResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    is_active: bool

    model_config = {"from_attributes": True}


class LabTestResponse(BaseModel):
    id: uuid.UUID
    key: str
    display_name: str
    loinc_code: str | None
    category: str
    specimen: str | None
    default_unit: str | None

    model_config = {"from_attributes": True}


class ReferenceRangeResponse(BaseModel):
    id: uuid.UUID
    test_id: uuid.UUID
    applies_to: str
    low: float | None
    high: float | None
    unit: str
    notes: str | None

    model_config = {"from_attributes": True}


class LabTestDetailResponse(LabTestResponse):
    reference_ranges: list[ReferenceRangeResponse]


class LabTestListResponse(BaseModel):
    items: list[LabTestResponse]
    total: int
    limit: int
    offset: int


class ReportDetailResponse(ReportResponse):
    results: list[ResultResponse]
