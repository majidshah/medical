import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.patient import get_patient_for_account


class ClinicalResourceError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


async def resolve_patient_or_404(
    session: AsyncSession, patient_id: uuid.UUID, account_id: uuid.UUID
):
    patient = await get_patient_for_account(session, patient_id, account_id)
    if patient is None:
        raise ClinicalResourceError("Patient not found", status_code=404)
    return patient
