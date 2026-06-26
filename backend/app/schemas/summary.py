import uuid
from datetime import date

from pydantic import BaseModel


class SummaryPatient(BaseModel):
    id: uuid.UUID
    medical_id: str
    full_name: str
    date_of_birth: date | None
    gender: str
    relationship_to_account: str


class SummaryCondition(BaseModel):
    id: uuid.UUID
    display_name: str
    code: str | None
    clinical_status: str
    onset_date: date | None


class SummaryMedication(BaseModel):
    id: uuid.UUID
    display_name: str
    dosage: str | None
    frequency: str | None
    status: str
    start_date: date | None


class SummaryAllergy(BaseModel):
    id: uuid.UUID
    display_name: str
    category: str
    criticality: str | None
    severity: str | None
    reaction: str | None


class SummaryResult(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    display_name: str
    value_numeric: float | None
    value_text: str | None
    unit: str | None
    effective_date: date
    normality_status: str


class SummaryCounts(BaseModel):
    conditions: int
    medications: int
    allergies: int
    immunizations: int
    family_history: int
    reports: int


class SummaryResponse(BaseModel):
    patient: SummaryPatient
    active_conditions: list[SummaryCondition]
    current_medications: list[SummaryMedication]
    allergies: list[SummaryAllergy]
    recent_results: list[SummaryResult]
    counts: SummaryCounts
