import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.models.account import Account
from app.schemas.summary import SummaryResponse
from app.services.summary import get_summary

router = APIRouter(tags=["summary"])


@router.get(
    "/patients/{patient_id}/summary",
    response_model=SummaryResponse,
)
async def summary_endpoint(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    recent_results: int = Query(default=10, ge=1, le=20),
) -> SummaryResponse:
    data = await get_summary(session, patient_id, account.id, recent_results)
    if data is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return SummaryResponse(**data)
