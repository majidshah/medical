import uuid

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    display_order: int = 0


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    display_order: int | None = None
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class PanelCreate(BaseModel):
    department_id: uuid.UUID
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    display_order: int = 0


class PanelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    display_order: int | None = None
    is_active: bool | None = None


class PanelResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    key: str
    name: str
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class TestCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=300)
    department_id: uuid.UUID
    panel_id: uuid.UUID | None = None
    loinc_code: str | None = None
    category: str = Field(min_length=1, max_length=50)
    specimen: str | None = None
    default_unit: str | None = None


class TestUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    department_id: uuid.UUID | None = None
    panel_id: uuid.UUID | None = None
    loinc_code: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    specimen: str | None = None
    default_unit: str | None = None
    is_active: bool | None = None


class TestResponse(BaseModel):
    id: uuid.UUID
    key: str
    display_name: str
    department_id: uuid.UUID
    panel_id: uuid.UUID | None
    loinc_code: str | None
    category: str
    specimen: str | None
    default_unit: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class RangeCreate(BaseModel):
    test_id: uuid.UUID
    applies_to: str = Field(min_length=1, max_length=50)
    low: float | None = None
    high: float | None = None
    unit: str = Field(min_length=1, max_length=50)
    notes: str | None = None
    lab_id: uuid.UUID | None = None
    needs_clinical_review: bool = False


class RangeUpdate(BaseModel):
    applies_to: str | None = Field(default=None, min_length=1, max_length=50)
    low: float | None = None
    high: float | None = None
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = None
    lab_id: uuid.UUID | None = None
    needs_clinical_review: bool | None = None


class RangeResponse(BaseModel):
    id: uuid.UUID
    test_id: uuid.UUID
    applies_to: str
    low: float | None
    high: float | None
    unit: str
    notes: str | None
    lab_id: uuid.UUID | None
    needs_clinical_review: bool

    model_config = {"from_attributes": True}


class LabCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class LabUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class LabResponse(BaseModel):
    id: uuid.UUID
    key: str
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
