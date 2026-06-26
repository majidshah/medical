import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab_reference_range import LabReferenceRange
from app.models.lab_result import LabResult
from app.models.lab_test_catalogue import LabTestCatalogue
from app.models.report import Report
from app.services.audit import log_event
from app.services.clinical import ClinicalResourceError, resolve_patient_or_404

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
