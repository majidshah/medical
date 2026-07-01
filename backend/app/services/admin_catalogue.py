"""Admin CRUD for the lab reference-data hierarchy: departments, panels,
tests, reference ranges, and labs.

This is reference data, not patient data — there is no account scoping
here, only the require_admin boundary enforced at the router. Every
write is audited. Departments/panels/tests/labs are soft-deleted
(is_active=False) because other rows FK to them (tests, ranges,
patient lab_results); reference ranges have no dependents and are hard
deleted.

applies_to on a reference range is deliberately free text, not an enum
(see CLAUDE.md's Reference data & roles rule) — 'female', 'male',
'general', or any future cohort value is accepted as-is.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import Lab
from app.models.lab_department import LabDepartment
from app.models.lab_panel import LabPanel
from app.models.lab_reference_range import LabReferenceRange
from app.models.lab_test_catalogue import LabTestCatalogue
from app.services.audit import log_event


class AdminCatalogueError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code


async def _unique_violation_or_raise(
    session: AsyncSession, exc: IntegrityError, conflict_detail: str
):
    await session.rollback()
    raise AdminCatalogueError(conflict_detail, status_code=409) from exc


# --- Departments ---------------------------------------------------------


async def list_departments(session: AsyncSession) -> list[LabDepartment]:
    result = await session.execute(select(LabDepartment).order_by(LabDepartment.display_order))
    return list(result.scalars().all())


async def create_department(
    session: AsyncSession, admin_id: uuid.UUID, *, key: str, name: str, display_order: int
) -> LabDepartment:
    dept = LabDepartment(key=key, name=name, display_order=display_order)
    session.add(dept)
    try:
        await session.flush()
    except IntegrityError as e:
        await _unique_violation_or_raise(session, e, f"Department key '{key}' already exists")
    await log_event(
        session,
        "admin.department_created",
        account_id=admin_id,
        detail=f"department_id={dept.id} key={key}",
    )
    await session.commit()
    return dept


async def get_department(session: AsyncSession, department_id: uuid.UUID) -> LabDepartment:
    dept = await session.get(LabDepartment, department_id)
    if dept is None:
        raise AdminCatalogueError("Department not found", status_code=404)
    return dept


async def update_department(
    session: AsyncSession, admin_id: uuid.UUID, department_id: uuid.UUID, **fields
) -> LabDepartment:
    dept = await get_department(session, department_id)
    changed = {k: v for k, v in fields.items() if v is not None and getattr(dept, k) != v}
    for key, value in changed.items():
        setattr(dept, key, value)
    if changed:
        await session.flush()
        await log_event(
            session,
            "admin.department_updated",
            account_id=admin_id,
            detail=f"department_id={dept.id} fields={sorted(changed)}",
        )
        await session.commit()
    return dept


# --- Panels ----------------------------------------------------------------


async def list_panels(
    session: AsyncSession, department_id: uuid.UUID | None = None
) -> list[LabPanel]:
    query = select(LabPanel).order_by(LabPanel.display_order)
    if department_id is not None:
        query = query.where(LabPanel.department_id == department_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def create_panel(
    session: AsyncSession,
    admin_id: uuid.UUID,
    *,
    department_id: uuid.UUID,
    key: str,
    name: str,
    display_order: int,
) -> LabPanel:
    await get_department(session, department_id)

    panel = LabPanel(department_id=department_id, key=key, name=name, display_order=display_order)
    session.add(panel)
    try:
        await session.flush()
    except IntegrityError as e:
        await _unique_violation_or_raise(
            session, e, f"Panel key '{key}' already exists in this department"
        )
    await log_event(
        session, "admin.panel_created", account_id=admin_id, detail=f"panel_id={panel.id} key={key}"
    )
    await session.commit()
    return panel


async def get_panel(session: AsyncSession, panel_id: uuid.UUID) -> LabPanel:
    panel = await session.get(LabPanel, panel_id)
    if panel is None:
        raise AdminCatalogueError("Panel not found", status_code=404)
    return panel


async def update_panel(
    session: AsyncSession, admin_id: uuid.UUID, panel_id: uuid.UUID, **fields
) -> LabPanel:
    panel = await get_panel(session, panel_id)
    changed = {k: v for k, v in fields.items() if v is not None and getattr(panel, k) != v}
    for key, value in changed.items():
        setattr(panel, key, value)
    if changed:
        await session.flush()
        await log_event(
            session,
            "admin.panel_updated",
            account_id=admin_id,
            detail=f"panel_id={panel.id} fields={sorted(changed)}",
        )
        await session.commit()
    return panel


# --- Tests -------------------------------------------------------------


async def list_tests(
    session: AsyncSession,
    *,
    department_id: uuid.UUID | None = None,
    panel_id: uuid.UUID | None = None,
) -> list[LabTestCatalogue]:
    query = select(LabTestCatalogue).order_by(LabTestCatalogue.display_name)
    if department_id is not None:
        query = query.where(LabTestCatalogue.department_id == department_id)
    if panel_id is not None:
        query = query.where(LabTestCatalogue.panel_id == panel_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def _validate_department_panel(
    session: AsyncSession, department_id: uuid.UUID, panel_id: uuid.UUID | None
) -> None:
    await get_department(session, department_id)
    if panel_id is None:
        return
    panel = await get_panel(session, panel_id)
    if panel.department_id != department_id:
        raise AdminCatalogueError("Panel does not belong to the given department", status_code=422)


async def create_test(
    session: AsyncSession,
    admin_id: uuid.UUID,
    *,
    key: str,
    display_name: str,
    department_id: uuid.UUID,
    panel_id: uuid.UUID | None,
    loinc_code: str | None,
    category: str,
    specimen: str | None,
    default_unit: str | None,
) -> LabTestCatalogue:
    await _validate_department_panel(session, department_id, panel_id)

    test = LabTestCatalogue(
        key=key,
        display_name=display_name,
        department_id=department_id,
        panel_id=panel_id,
        loinc_code=loinc_code,
        category=category,
        specimen=specimen,
        default_unit=default_unit,
    )
    session.add(test)
    try:
        await session.flush()
    except IntegrityError as e:
        await _unique_violation_or_raise(session, e, f"Test key '{key}' already exists")
    await log_event(
        session, "admin.test_created", account_id=admin_id, detail=f"test_id={test.id} key={key}"
    )
    await session.commit()
    return test


async def get_test(session: AsyncSession, test_id: uuid.UUID) -> LabTestCatalogue:
    test = await session.get(LabTestCatalogue, test_id)
    if test is None:
        raise AdminCatalogueError("Test not found", status_code=404)
    return test


async def update_test(
    session: AsyncSession, admin_id: uuid.UUID, test_id: uuid.UUID, **fields
) -> LabTestCatalogue:
    test = await get_test(session, test_id)
    changed = {k: v for k, v in fields.items() if v is not None and getattr(test, k) != v}

    new_department_id = changed.get("department_id", test.department_id)
    new_panel_id = changed.get("panel_id", test.panel_id)
    if "department_id" in changed or "panel_id" in changed:
        await _validate_department_panel(session, new_department_id, new_panel_id)

    for key, value in changed.items():
        setattr(test, key, value)
    if changed:
        try:
            await session.flush()
        except IntegrityError as e:
            await _unique_violation_or_raise(
                session, e, f"Test key '{test.key}' conflicts with an existing test"
            )
        await log_event(
            session,
            "admin.test_updated",
            account_id=admin_id,
            detail=f"test_id={test.id} fields={sorted(changed)}",
        )
        await session.commit()
    return test


# --- Reference ranges ----------------------------------------------------


async def list_ranges(session: AsyncSession, test_id: uuid.UUID) -> list[LabReferenceRange]:
    await get_test(session, test_id)
    result = await session.execute(
        select(LabReferenceRange).where(LabReferenceRange.test_id == test_id)
    )
    return list(result.scalars().all())


async def _validate_lab(session: AsyncSession, lab_id: uuid.UUID | None) -> None:
    if lab_id is None:
        return
    lab = await session.get(Lab, lab_id)
    if lab is None:
        raise AdminCatalogueError("Lab not found", status_code=404)


async def create_range(
    session: AsyncSession,
    admin_id: uuid.UUID,
    *,
    test_id: uuid.UUID,
    applies_to: str,
    low: float | None,
    high: float | None,
    unit: str,
    notes: str | None,
    lab_id: uuid.UUID | None,
    needs_clinical_review: bool,
) -> LabReferenceRange:
    await get_test(session, test_id)
    await _validate_lab(session, lab_id)

    range_ = LabReferenceRange(
        test_id=test_id,
        applies_to=applies_to,
        low=low,
        high=high,
        unit=unit,
        notes=notes,
        lab_id=lab_id,
        needs_clinical_review=needs_clinical_review,
    )
    session.add(range_)
    await session.flush()
    await log_event(
        session,
        "admin.range_created",
        account_id=admin_id,
        detail=f"range_id={range_.id} test_id={test_id} applies_to={applies_to}",
    )
    await session.commit()
    return range_


async def get_range(session: AsyncSession, range_id: uuid.UUID) -> LabReferenceRange:
    range_ = await session.get(LabReferenceRange, range_id)
    if range_ is None:
        raise AdminCatalogueError("Reference range not found", status_code=404)
    return range_


async def update_range(
    session: AsyncSession, admin_id: uuid.UUID, range_id: uuid.UUID, **fields
) -> LabReferenceRange:
    range_ = await get_range(session, range_id)
    if "lab_id" in fields and fields["lab_id"] is not None:
        await _validate_lab(session, fields["lab_id"])

    changed = {k: v for k, v in fields.items() if v is not None and getattr(range_, k) != v}
    for key, value in changed.items():
        setattr(range_, key, value)
    if changed:
        await session.flush()
        await log_event(
            session,
            "admin.range_updated",
            account_id=admin_id,
            detail=f"range_id={range_.id} fields={sorted(changed)}",
        )
        await session.commit()
    return range_


async def delete_range(session: AsyncSession, admin_id: uuid.UUID, range_id: uuid.UUID) -> None:
    range_ = await get_range(session, range_id)
    await session.delete(range_)
    await session.flush()
    await log_event(
        session, "admin.range_deleted", account_id=admin_id, detail=f"range_id={range_id}"
    )
    await session.commit()


# --- Labs ------------------------------------------------------------------


async def list_labs(session: AsyncSession) -> list[Lab]:
    result = await session.execute(select(Lab).order_by(Lab.name))
    return list(result.scalars().all())


async def create_lab(session: AsyncSession, admin_id: uuid.UUID, *, key: str, name: str) -> Lab:
    lab = Lab(key=key, name=name)
    session.add(lab)
    try:
        await session.flush()
    except IntegrityError as e:
        await _unique_violation_or_raise(session, e, f"Lab key '{key}' already exists")
    await log_event(
        session, "admin.lab_created", account_id=admin_id, detail=f"lab_id={lab.id} key={key}"
    )
    await session.commit()
    return lab


async def get_lab(session: AsyncSession, lab_id: uuid.UUID) -> Lab:
    lab = await session.get(Lab, lab_id)
    if lab is None:
        raise AdminCatalogueError("Lab not found", status_code=404)
    return lab


async def update_lab(
    session: AsyncSession, admin_id: uuid.UUID, lab_id: uuid.UUID, **fields
) -> Lab:
    lab = await get_lab(session, lab_id)
    changed = {k: v for k, v in fields.items() if v is not None and getattr(lab, k) != v}
    for key, value in changed.items():
        setattr(lab, key, value)
    if changed:
        await session.flush()
        await log_event(
            session,
            "admin.lab_updated",
            account_id=admin_id,
            detail=f"lab_id={lab.id} fields={sorted(changed)}",
        )
        await session.commit()
    return lab
