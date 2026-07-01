import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_department import LabDepartment
from app.models.lab_panel import LabPanel
from app.models.lab_reference_range import LabReferenceRange
from app.models.lab_result import LabResult
from app.models.lab_test_catalogue import LabTestCatalogue
from app.models.patient import Patient
from app.models.report import Report
from app.models.stored_file import StoredFile
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404
from app.services.normality import NormalityResult, evaluate, select_range

LabError = ClinicalResourceError


async def create_report(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Report:
    patient = await resolve_patient_or_404(session, patient_id, account_id)

    report = Report(patient_id=patient.id, account_id=patient.account_id, **fields)
    session.add(report)
    await session.flush()
    await log_event(
        session,
        "report_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} report_id={report.id}",
    )
    await session.commit()
    return report


async def list_reports(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    category: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Report], int]:
    await resolve_patient_or_404(session, patient_id, account_id)

    filters = [
        Report.patient_id == patient_id,
        Report.account_id == account_id,
        Report.is_active.is_(True),
    ]
    if category:
        filters.append(Report.category == category)
    if from_date:
        filters.append(Report.report_date >= from_date)
    if to_date:
        filters.append(Report.report_date <= to_date)

    base = select(Report).where(*filters)
    count_q = select(func.count()).select_from(Report).where(*filters)
    query = base.order_by(Report.report_date.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def get_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Report | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(Report).where(
            Report.id == report_id,
            Report.patient_id == patient_id,
            Report.account_id == account_id,
            Report.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> Report:
    report = await get_report(session, report_id, patient_id, account_id)
    if report is None:
        raise LabError("Report not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(report, key, value)

    await session.flush()
    await log_event(
        session,
        "report_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} report_id={report.id}",
    )
    await session.commit()
    return report


async def soft_delete_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    report = await get_report(session, report_id, patient_id, account_id)
    if report is None:
        raise LabError("Report not found", status_code=404)

    report.is_active = False

    results = await session.execute(
        select(LabResult).where(
            LabResult.report_id == report.id,
            LabResult.is_active.is_(True),
        )
    )
    for r in results.scalars().all():
        r.is_active = False

    await session.flush()
    await log_event(
        session,
        "report_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} report_id={report.id}",
    )
    await session.commit()


async def create_result(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> LabResult:
    patient = await resolve_patient_or_404(session, patient_id, account_id)
    report = await get_report(session, report_id, patient_id, account_id)
    if report is None:
        raise LabError("Report not found", status_code=404)

    test_id = fields.get("test_id")
    if test_id:
        test = await session.execute(select(LabTestCatalogue).where(LabTestCatalogue.id == test_id))
        cat_entry = test.scalar_one_or_none()
        if cat_entry is None:
            raise LabError("Lab test not found in catalogue", status_code=404)
        fields.setdefault("display_name", cat_entry.display_name)
        fields.setdefault("loinc_code", cat_entry.loinc_code)
        if fields.get("unit") is None:
            fields["unit"] = cat_entry.default_unit

    lab_result = LabResult(
        report_id=report.id,
        patient_id=patient.id,
        account_id=patient.account_id,
        **fields,
    )
    session.add(lab_result)
    await session.flush()
    await log_event(
        session,
        "result_created",
        account_id=account_id,
        detail=f"patient_id={patient.id} result_id={lab_result.id}",
    )
    await session.commit()
    return lab_result


async def list_results_for_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> list[LabResult]:
    await resolve_patient_or_404(session, patient_id, account_id)
    report = await get_report(session, report_id, patient_id, account_id)
    if report is None:
        raise LabError("Report not found", status_code=404)

    result = await session.execute(
        select(LabResult).where(
            LabResult.report_id == report_id,
            LabResult.patient_id == patient_id,
            LabResult.account_id == account_id,
            LabResult.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def get_result(
    session: AsyncSession,
    result_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> LabResult | None:
    await resolve_patient_or_404(session, patient_id, account_id)
    result = await session.execute(
        select(LabResult).where(
            LabResult.id == result_id,
            LabResult.patient_id == patient_id,
            LabResult.account_id == account_id,
            LabResult.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_result(
    session: AsyncSession,
    result_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    **fields,
) -> LabResult:
    lab_result = await get_result(session, result_id, patient_id, account_id)
    if lab_result is None:
        raise LabError("Result not found", status_code=404)

    for key, value in fields.items():
        if value is not None:
            setattr(lab_result, key, value)

    await session.flush()
    await log_event(
        session,
        "result_updated",
        account_id=account_id,
        detail=f"patient_id={patient_id} result_id={lab_result.id}",
    )
    await session.commit()
    return lab_result


async def soft_delete_result(
    session: AsyncSession,
    result_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> None:
    lab_result = await get_result(session, result_id, patient_id, account_id)
    if lab_result is None:
        raise LabError("Result not found", status_code=404)

    lab_result.is_active = False
    await session.flush()
    await log_event(
        session,
        "result_deleted",
        account_id=account_id,
        detail=f"patient_id={patient_id} result_id={lab_result.id}",
    )
    await session.commit()


async def list_catalogue(
    session: AsyncSession,
    *,
    category: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[LabTestCatalogue], int]:
    filters = [LabTestCatalogue.is_active.is_(True)]
    if category:
        filters.append(LabTestCatalogue.category == category)
    if q:
        filters.append(LabTestCatalogue.display_name.ilike(f"%{q}%"))

    base = select(LabTestCatalogue).where(*filters)
    count_q = select(func.count()).select_from(LabTestCatalogue).where(*filters)
    query = base.order_by(LabTestCatalogue.display_name).limit(limit).offset(offset)

    result = await session.execute(query)
    items = list(result.scalars().all())
    total = (await session.execute(count_q)).scalar_one()
    return items, total


async def list_browse_departments(session: AsyncSession) -> list[LabDepartment]:
    result = await session.execute(
        select(LabDepartment)
        .where(LabDepartment.is_active.is_(True))
        .order_by(LabDepartment.display_order)
    )
    return list(result.scalars().all())


async def list_browse_panels(session: AsyncSession, department_id: uuid.UUID) -> list[LabPanel]:
    result = await session.execute(
        select(LabPanel)
        .where(LabPanel.department_id == department_id, LabPanel.is_active.is_(True))
        .order_by(LabPanel.display_order)
    )
    return list(result.scalars().all())


async def list_tests_for_panel(
    session: AsyncSession, panel_id: uuid.UUID
) -> list[LabTestCatalogue]:
    result = await session.execute(
        select(LabTestCatalogue)
        .where(
            LabTestCatalogue.panel_id == panel_id,
            LabTestCatalogue.is_active.is_(True),
        )
        .order_by(LabTestCatalogue.display_name)
    )
    return list(result.scalars().all())


async def get_catalogue_detail(
    session: AsyncSession, test_id: uuid.UUID
) -> tuple[LabTestCatalogue | None, list[LabReferenceRange]]:
    result = await session.execute(select(LabTestCatalogue).where(LabTestCatalogue.id == test_id))
    test = result.scalar_one_or_none()
    if test is None:
        return None, []

    ranges_result = await session.execute(
        select(LabReferenceRange).where(LabReferenceRange.test_id == test_id)
    )
    ranges = list(ranges_result.scalars().all())
    return test, ranges


async def compute_normality_for_result(
    session: AsyncSession,
    lab_result: LabResult,
    patient_gender: str | None = None,
) -> NormalityResult:
    if lab_result.test_id is None:
        return NormalityResult(status="unknown", reason="No catalogue test linked")

    ranges_result = await session.execute(
        select(LabReferenceRange).where(LabReferenceRange.test_id == lab_result.test_id)
    )
    ranges = [
        {
            "applies_to": r.applies_to,
            "low": float(r.low) if r.low is not None else None,
            "high": float(r.high) if r.high is not None else None,
            "unit": r.unit,
        }
        for r in ranges_result.scalars().all()
    ]

    chosen = select_range(ranges, patient_gender)
    if chosen is None:
        return NormalityResult(status="unknown", reason="No applicable reference range")

    return evaluate(
        value_numeric=(
            float(lab_result.value_numeric) if lab_result.value_numeric is not None else None
        ),
        value_text=lab_result.value_text,
        result_unit=lab_result.unit,
        range_low=chosen.get("low"),
        range_high=chosen.get("high"),
        range_unit=chosen.get("unit"),
        range_applies_to=chosen.get("applies_to"),
    )


async def get_enriched_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> tuple[Report | None, list[tuple[LabResult, NormalityResult]], StoredFile | None]:
    report = await get_report(session, report_id, patient_id, account_id)
    if report is None:
        return None, [], None

    results = await list_results_for_report(session, report_id, patient_id, account_id)

    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    patient_gender = patient.gender if patient else None

    enriched = []
    for r in results:
        normality = await compute_normality_for_result(session, r, patient_gender)
        enriched.append((r, normality))

    file_ref = None
    if report.file_id:
        file_result = await session.execute(
            select(StoredFile).where(
                StoredFile.id == report.file_id,
                StoredFile.is_active.is_(True),
            )
        )
        file_ref = file_result.scalar_one_or_none()

    await log_event(
        session,
        "report_viewed",
        account_id=account_id,
        detail=f"patient_id={patient_id} report_id={report.id}",
    )
    await session.commit()

    return report, enriched, file_ref


async def get_timeline(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    *,
    category: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    patient = await resolve_patient_or_404(session, patient_id, account_id)
    patient_gender = patient.gender

    filters = [
        Report.patient_id == patient_id,
        Report.account_id == account_id,
        Report.is_active.is_(True),
    ]
    if category:
        filters.append(Report.category == category)
    if from_date:
        filters.append(Report.report_date >= from_date)
    if to_date:
        filters.append(Report.report_date <= to_date)

    count_q = select(func.count()).select_from(Report).where(*filters)
    total = (await session.execute(count_q)).scalar_one()

    query = (
        select(Report)
        .where(*filters)
        .order_by(Report.report_date.desc())
        .limit(limit)
        .offset(offset)
    )
    reports = list((await session.execute(query)).scalars().all())

    entries = []
    for report in reports:
        results = await session.execute(
            select(LabResult).where(
                LabResult.report_id == report.id,
                LabResult.is_active.is_(True),
            )
        )
        result_list = list(results.scalars().all())

        has_oor = False
        for r in result_list:
            n = await compute_normality_for_result(session, r, patient_gender)
            if n.status in ("below_low", "above_high"):
                has_oor = True
                break

        entries.append(
            {
                "id": report.id,
                "report_date": report.report_date,
                "category": report.category,
                "lab_name": report.lab_name,
                "result_count": len(result_list),
                "has_out_of_range": has_oor,
            }
        )

    return entries, total


async def get_lab_trend(
    session: AsyncSession,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
    test_key_or_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    patient = await resolve_patient_or_404(session, patient_id, account_id)
    patient_gender = patient.gender

    try:
        test_uuid = uuid.UUID(test_key_or_id)
        test_result = await session.execute(
            select(LabTestCatalogue).where(LabTestCatalogue.id == test_uuid)
        )
    except ValueError:
        test_result = await session.execute(
            select(LabTestCatalogue).where(LabTestCatalogue.key == test_key_or_id)
        )

    test = test_result.scalar_one_or_none()
    if test is None:
        raise LabError("Lab test not found", status_code=404)

    ranges_result = await session.execute(
        select(LabReferenceRange).where(LabReferenceRange.test_id == test.id)
    )
    ranges = [
        {
            "applies_to": r.applies_to,
            "low": float(r.low) if r.low is not None else None,
            "high": float(r.high) if r.high is not None else None,
            "unit": r.unit,
        }
        for r in ranges_result.scalars().all()
    ]
    chosen = select_range(ranges, patient_gender)

    filters = [
        LabResult.patient_id == patient_id,
        LabResult.account_id == account_id,
        LabResult.test_id == test.id,
        LabResult.is_active.is_(True),
    ]
    if from_date:
        filters.append(LabResult.effective_date >= from_date)
    if to_date:
        filters.append(LabResult.effective_date <= to_date)

    query = select(LabResult).where(*filters).order_by(LabResult.effective_date.asc())
    results = list((await session.execute(query)).scalars().all())

    has_numeric = any(r.value_numeric is not None for r in results)

    points = []
    for r in results:
        n = await compute_normality_for_result(session, r, patient_gender)
        points.append(
            {
                "effective_date": r.effective_date,
                "value": float(r.value_numeric) if r.value_numeric is not None else None,
                "unit": r.unit,
                "normality_status": n.status,
            }
        )

    return {
        "test_key": test.key,
        "test_display_name": test.display_name,
        "chartable": has_numeric,
        "range_low": chosen["low"] if chosen else None,
        "range_high": chosen["high"] if chosen else None,
        "range_unit": chosen["unit"] if chosen else None,
        "points": points,
    }


async def get_result_normality(
    session: AsyncSession,
    result_id: uuid.UUID,
    patient_id: uuid.UUID,
    account_id: uuid.UUID,
) -> NormalityResult:
    lab_result = await get_result(session, result_id, patient_id, account_id)
    if lab_result is None:
        raise LabError("Result not found", status_code=404)

    patient_result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = patient_result.scalar_one_or_none()
    patient_gender = patient.gender if patient else None

    return await compute_normality_for_result(session, lab_result, patient_gender)
