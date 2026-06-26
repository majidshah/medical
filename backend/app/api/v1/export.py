import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.services.audit import log_event
from app.services.export_fhir import build_fhir_bundle
from app.services.export_pdf import generate_pdf

router = APIRouter(prefix="/patients/{patient_id}/export", tags=["export"])


@router.get("/fhir")
async def export_fhir(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    bundle = await build_fhir_bundle(session, patient_id, account.id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    await log_event(
        session,
        "export_generated",
        account_id=account.id,
        detail=f"patient_id={patient_id} format=fhir",
    )
    await session.commit()

    import json

    return Response(
        content=json.dumps(bundle, default=str),
        media_type="application/fhir+json",
        headers={"Content-Disposition": "attachment; filename=health-record.fhir.json"},
    )


@router.get("/pdf")
async def export_pdf(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    pdf_bytes = await generate_pdf(session, patient_id, account.id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    await log_event(
        session,
        "export_generated",
        account_id=account.id,
        detail=f"patient_id={patient_id} format=pdf",
    )
    await session.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=health-summary.pdf"},
    )
