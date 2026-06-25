import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class FamilyRelationship(StrEnum):
    mother = "mother"
    father = "father"
    brother = "brother"
    sister = "sister"
    grandfather_paternal = "grandfather-paternal"
    grandmother_paternal = "grandmother-paternal"
    grandfather_maternal = "grandfather-maternal"
    grandmother_maternal = "grandmother-maternal"
    son = "son"
    daughter = "daughter"
    other = "other"


class FamilyHistoryCreate(BaseModel):
    relationship: FamilyRelationship
    condition_display_name: str = Field(min_length=1, max_length=500)
    condition_code: str | None = None
    condition_code_system: str = "http://snomed.info/sct"
    onset_age: int | None = None
    deceased: bool | None = None
    notes: str | None = None


class FamilyHistoryUpdate(BaseModel):
    relationship: FamilyRelationship | None = None
    condition_display_name: str | None = Field(default=None, min_length=1, max_length=500)
    condition_code: str | None = None
    condition_code_system: str | None = None
    onset_age: int | None = None
    deceased: bool | None = None
    notes: str | None = None


class FamilyHistoryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    account_id: uuid.UUID
    relationship: str
    condition_code_system: str
    condition_code: str | None
    condition_display_name: str
    onset_age: int | None
    deceased: bool | None
    notes: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class FamilyHistoryListResponse(BaseModel):
    items: list[FamilyHistoryResponse]
    total: int
    limit: int
    offset: int
