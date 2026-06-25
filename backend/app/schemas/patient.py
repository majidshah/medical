import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Gender(StrEnum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class Relationship(StrEnum):
    self_ = "self"
    child = "child"
    spouse = "spouse"
    parent = "parent"
    other = "other"


def normalize_cnic(value: str) -> str:
    digits = value.replace("-", "")
    if not digits.isdigit() or len(digits) != 13:
        raise ValueError("CNIC must contain exactly 13 digits")
    return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date | None = None
    gender: Gender
    relationship_to_account: Relationship
    cnic: str | None = None
    guardian_patient_id: uuid.UUID | None = None

    @field_validator("cnic")
    @classmethod
    def validate_cnic(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_cnic(v)


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    date_of_birth: date | None = None
    gender: Gender | None = None
    relationship_to_account: Relationship | None = None


class PatientResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    medical_id: str
    full_name: str
    date_of_birth: date | None
    gender: str
    relationship_to_account: str
    has_cnic: bool
    guardian_patient_id: uuid.UUID | None
    is_active: bool

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    limit: int
    offset: int
