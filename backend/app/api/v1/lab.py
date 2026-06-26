import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_account
from app.db.session import get_session
from app.fhir.observation import to_fhir
from app.models.account import Account
from app.schemas.lab import (
    EnrichedReportDetailResponse,
    EnrichedResultResponse,
    LabTestDetailResponse,
    LabTestListResponse,
    LabTestResponse,
    LabTrendPoint,
    LabTrendResponse,
    NormalityResponse,
    ReferenceRangeResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportUpdate,
    ResultCreate,
    ResultListResponse,
    ResultResponse,
    ResultUpdate,
    StoredFileResponse,
    TimelineEntry,
    TimelineResponse,
)
from app.services.lab import (
    LabError,
    create_report,
    create_result,
    get_catalogue_detail,
    get_enriched_report,
    get_lab_trend,
    get_result,
    get_result_normality,
    get_timeline,
    list_catalogue,
    list_reports,
    list_results_for_report,
    soft_delete_report,
    soft_delete_result,
    update_report,
    update_result,
)

router = APIRouter(tags=["lab"])


@router.post("/patients/{patient_id}/reports", response_model=ReportResponse, status_code=201)
async def create_report_endpoint(
    patient_id: uuid.UUID,
    body: ReportCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportResponse:
    try:
        report = await create_report(
            session,
            patient_id,
            account.id,
            category=body.category.value,
            report_date=body.report_date,
            lab_name=body.lab_name,
            file_id=body.file_id,
            notes=body.notes,
        )
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ReportResponse.model_validate(report)


@router.get("/patients/{patient_id}/reports", response_model=ReportListResponse)
async def list_reports_endpoint(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    category: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReportListResponse:
    try:
        items, total = await list_reports(
            session,
            patient_id,
            account.id,
            category=category,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/patients/{patient_id}/reports/{report_id}",
    response_model=EnrichedReportDetailResponse,
)
async def get_report_endpoint(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EnrichedReportDetailResponse:
    try:
        report, enriched_results, file_ref = await get_enriched_report(
            session, report_id, patient_id, account.id
        )
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    results_out = []
    for r, n in enriched_results:
        results_out.append(
            EnrichedResultResponse(
                **ResultResponse.model_validate(r).model_dump(),
                normality=NormalityResponse(
                    status=n.status,
                    range_low=n.range_low,
                    range_high=n.range_high,
                    range_unit=n.range_unit,
                    range_applies_to=n.range_applies_to,
                    reason=n.reason,
                ),
            )
        )

    return EnrichedReportDetailResponse(
        **ReportResponse.model_validate(report).model_dump(),
        results=results_out,
        file_ref=StoredFileResponse.model_validate(file_ref) if file_ref else None,
    )


@router.patch("/patients/{patient_id}/reports/{report_id}", response_model=ReportResponse)
async def update_report_endpoint(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ReportUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportResponse:
    fields = body.model_dump(exclude_unset=True)
    if "category" in fields and fields["category"] is not None:
        fields["category"] = fields["category"].value
    try:
        report = await update_report(session, report_id, patient_id, account.id, **fields)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ReportResponse.model_validate(report)


@router.delete("/patients/{patient_id}/reports/{report_id}", status_code=204)
async def delete_report_endpoint(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_report(session, report_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.post(
    "/patients/{patient_id}/reports/{report_id}/results",
    response_model=ResultResponse,
    status_code=201,
)
async def create_result_endpoint(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    body: ResultCreate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResultResponse:
    try:
        result = await create_result(
            session,
            report_id,
            patient_id,
            account.id,
            test_id=body.test_id,
            display_name=body.display_name,
            value_numeric=body.value_numeric,
            value_text=body.value_text,
            unit=body.unit,
            effective_date=body.effective_date,
            notes=body.notes,
        )
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ResultResponse.model_validate(result)


@router.get(
    "/patients/{patient_id}/reports/{report_id}/results",
    response_model=ResultListResponse,
)
async def list_results_endpoint(
    patient_id: uuid.UUID,
    report_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResultListResponse:
    try:
        items = await list_results_for_report(session, report_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ResultListResponse(
        items=[ResultResponse.model_validate(r) for r in items],
        total=len(items),
        limit=len(items),
        offset=0,
    )


@router.get("/patients/{patient_id}/results/{result_id}", response_model=ResultResponse)
async def get_result_endpoint(
    patient_id: uuid.UUID,
    result_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResultResponse:
    try:
        result = await get_result(session, result_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return ResultResponse.model_validate(result)


@router.patch("/patients/{patient_id}/results/{result_id}", response_model=ResultResponse)
async def update_result_endpoint(
    patient_id: uuid.UUID,
    result_id: uuid.UUID,
    body: ResultUpdate,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ResultResponse:
    fields = body.model_dump(exclude_unset=True)
    try:
        result = await update_result(session, result_id, patient_id, account.id, **fields)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return ResultResponse.model_validate(result)


@router.delete("/patients/{patient_id}/results/{result_id}", status_code=204)
async def delete_result_endpoint(
    patient_id: uuid.UUID,
    result_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    try:
        await soft_delete_result(session, result_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None


@router.get("/patients/{patient_id}/results/{result_id}/fhir")
async def get_result_fhir(
    patient_id: uuid.UUID,
    result_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    try:
        result = await get_result(session, result_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return to_fhir(
        observation_id=result.id,
        patient_reference_id=patient_id,
        loinc_code=result.loinc_code,
        display_label=result.display_name,
        effective_date=result.effective_date.isoformat(),
        value_numeric=float(result.value_numeric) if result.value_numeric is not None else None,
        value_text=result.value_text,
        unit=result.unit,
        category_code="laboratory",
        category_display="Laboratory",
    )


@router.get("/lab-catalogue", response_model=LabTestListResponse)
async def list_catalogue_endpoint(
    _account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> LabTestListResponse:
    items, total = await list_catalogue(session, category=category, q=q, limit=limit, offset=offset)
    return LabTestListResponse(
        items=[LabTestResponse.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/lab-catalogue/{test_id}", response_model=LabTestDetailResponse)
async def get_catalogue_detail_endpoint(
    test_id: uuid.UUID,
    _account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LabTestDetailResponse:
    test, ranges = await get_catalogue_detail(session, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Lab test not found")
    return LabTestDetailResponse(
        **LabTestResponse.model_validate(test).model_dump(),
        reference_ranges=[ReferenceRangeResponse.model_validate(r) for r in ranges],
    )


@router.get("/patients/{patient_id}/timeline", response_model=TimelineResponse)
async def timeline_endpoint(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    category: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TimelineResponse:
    try:
        entries, total = await get_timeline(
            session,
            patient_id,
            account.id,
            category=category,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return TimelineResponse(
        items=[TimelineEntry(**e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/patients/{patient_id}/results/{result_id}/normality",
    response_model=NormalityResponse,
)
async def normality_endpoint(
    patient_id: uuid.UUID,
    result_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NormalityResponse:
    try:
        n = await get_result_normality(session, result_id, patient_id, account.id)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return NormalityResponse(
        status=n.status,
        range_low=n.range_low,
        range_high=n.range_high,
        range_unit=n.range_unit,
        range_applies_to=n.range_applies_to,
        reason=n.reason,
    )


@router.get(
    "/patients/{patient_id}/lab-trend",
    response_model=LabTrendResponse,
)
async def lab_trend_endpoint(
    patient_id: uuid.UUID,
    account: Annotated[Account, Depends(get_current_account)],
    session: Annotated[AsyncSession, Depends(get_session)],
    test: str = Query(alias="test"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> LabTrendResponse:
    try:
        data = await get_lab_trend(session, patient_id, account.id, test, from_date, to_date)
    except LabError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    return LabTrendResponse(
        test_key=data["test_key"],
        test_display_name=data["test_display_name"],
        chartable=data["chartable"],
        range_low=data["range_low"],
        range_high=data["range_high"],
        range_unit=data["range_unit"],
        points=[LabTrendPoint(**p) for p in data["points"]],
    )
