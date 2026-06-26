import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.schemas.lab import StoredFileResponse
from app.services.file import FileError, download_file, soft_delete_file, upload_file

router = APIRouter(prefix="/patients/{patient_id}/files", tags=["files"])


@router.post("", response_model=StoredFileResponse, status_code=201)
async def upload(
    patient_id: uuid.UUID,
    file: UploadFile,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StoredFileResponse:
    data = await file.read()
    try:
        stored = await upload_file(
            session,
            patient_id,
            account.id,
            data=data,
            filename=file.filename or "unnamed",
            content_type=file.content_type or "application/octet-stream",
        )
    except FileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return StoredFileResponse.model_validate(stored)


@router.get("/{file_id}")
async def download(
    patient_id: uuid.UUID,
    file_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    try:
        stored, data = await download_file(session, file_id, patient_id, account.id)
    except FileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return Response(
        content=data,
        media_type=stored.content_type,
        headers={"Content-Disposition": f'inline; filename="{stored.original_filename}"'},
    )


@router.delete("/{file_id}", status_code=204)
async def delete(
    patient_id: uuid.UUID,
    file_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_file(session, file_id, patient_id, account.id)
    except FileError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
