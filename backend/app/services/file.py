import uuid
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.stored_file import StoredFile
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404
from app.services.storage import ALLOWED_CONTENT_TYPES, get_storage_backend

FileError = ClinicalResourceError


async def upload_file(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    data: bytes,
    filename: str,
    content_type: str,
) -> StoredFile:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    if content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise FileError(
            f"File type '{content_type}' not allowed. Allowed: {allowed}",
            status_code=422,
        )

    if len(data) > settings.max_upload_size_bytes:
        raise FileError(
            f"File exceeds maximum size of {settings.max_upload_size_bytes} bytes",
            status_code=422,
        )

    safe_filename = PurePosixPath(filename).name or "unnamed"

    backend = get_storage_backend()
    storage_key = await backend.save(data, content_type)

    stored = StoredFile(
        account_id=patient.account_id,
        patient_id=patient.id,
        original_filename=safe_filename,
        content_type=content_type,
        size_bytes=len(data),
        storage_key=storage_key,
    )
    session.add(stored)
    await session.flush()
    await log_event(
        session,
        "file_uploaded",
        account_id=account_id,
        detail=f"patient_id={patient.id} file_id={stored.id} filename={safe_filename}",
    )
    await session.commit()
    return stored


async def get_file_record(
    session: AsyncSession,
    file_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> StoredFile | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.patient_id == patient_id,
            StoredFile.account_id == account_id,
            StoredFile.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def download_file(
    session: AsyncSession,
    file_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> tuple[StoredFile, bytes]:
    stored = await get_file_record(session, file_id, patient_id, account_id)
    if stored is None:
        raise FileError("File not found", status_code=404)

    backend = get_storage_backend()
    data = await backend.load(stored.storage_key)

    await log_event(
        session,
        "file_downloaded",
        account_id=account_id,
        detail=f"patient_id={patient_id} file_id={stored.id}",
    )
    await session.commit()
    return stored, data


async def soft_delete_file(
    session: AsyncSession,
    file_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    stored = await get_file_record(session, file_id, patient_id, account_id)
    if stored is None:
        raise FileError("File not found", status_code=404)

    stored.is_active = False
    await session.flush()
    await log_event(
        session,
        "file_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} file_id={stored.id}",
    )
    await session.commit()
