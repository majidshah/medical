import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.account import Account
from app.schemas.admin_catalogue import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    LabCreate,
    LabResponse,
    LabUpdate,
    PanelCreate,
    PanelResponse,
    PanelUpdate,
    RangeCreate,
    RangeResponse,
    RangeUpdate,
    TestCreate,
    TestResponse,
    TestUpdate,
)
from app.services import admin_catalogue as svc

router = APIRouter(prefix="/admin", tags=["admin-catalogue"])


def _raise(e: svc.AdminCatalogueError):
    raise HTTPException(status_code=e.status_code, detail=e.detail) from None


# --- Departments ---------------------------------------------------------


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await svc.list_departments(session)


@router.post("/departments", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.create_department(
            session, admin.id, key=body.key, name=body.name, display_order=body.display_order
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: uuid.UUID,
    body: DepartmentUpdate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_department(
            session, admin.id, department_id, **body.model_dump(exclude_unset=True)
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.delete("/departments/{department_id}", response_model=DepartmentResponse)
async def deactivate_department(
    department_id: uuid.UUID,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_department(session, admin.id, department_id, is_active=False)
    except svc.AdminCatalogueError as e:
        _raise(e)


# --- Panels ----------------------------------------------------------------


@router.get("/panels", response_model=list[PanelResponse])
async def list_panels(
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    department_id: uuid.UUID | None = Query(default=None),
):
    return await svc.list_panels(session, department_id=department_id)


@router.post("/panels", response_model=PanelResponse, status_code=201)
async def create_panel(
    body: PanelCreate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.create_panel(
            session,
            admin.id,
            department_id=body.department_id,
            key=body.key,
            name=body.name,
            display_order=body.display_order,
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.patch("/panels/{panel_id}", response_model=PanelResponse)
async def update_panel(
    panel_id: uuid.UUID,
    body: PanelUpdate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_panel(
            session, admin.id, panel_id, **body.model_dump(exclude_unset=True)
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.delete("/panels/{panel_id}", response_model=PanelResponse)
async def deactivate_panel(
    panel_id: uuid.UUID,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_panel(session, admin.id, panel_id, is_active=False)
    except svc.AdminCatalogueError as e:
        _raise(e)


# --- Tests -----------------------------------------------------------------


@router.get("/tests", response_model=list[TestResponse])
async def list_tests(
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    department_id: uuid.UUID | None = Query(default=None),
    panel_id: uuid.UUID | None = Query(default=None),
):
    return await svc.list_tests(session, department_id=department_id, panel_id=panel_id)


@router.post("/tests", response_model=TestResponse, status_code=201)
async def create_test(
    body: TestCreate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.create_test(session, admin.id, **body.model_dump())
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.patch("/tests/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: uuid.UUID,
    body: TestUpdate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_test(
            session, admin.id, test_id, **body.model_dump(exclude_unset=True)
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.delete("/tests/{test_id}", response_model=TestResponse)
async def deactivate_test(
    test_id: uuid.UUID,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_test(session, admin.id, test_id, is_active=False)
    except svc.AdminCatalogueError as e:
        _raise(e)


# --- Reference ranges ------------------------------------------------------


@router.get("/tests/{test_id}/ranges", response_model=list[RangeResponse])
async def list_ranges(
    test_id: uuid.UUID,
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.list_ranges(session, test_id)
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.post("/ranges", response_model=RangeResponse, status_code=201)
async def create_range(
    body: RangeCreate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.create_range(session, admin.id, **body.model_dump())
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.patch("/ranges/{range_id}", response_model=RangeResponse)
async def update_range(
    range_id: uuid.UUID,
    body: RangeUpdate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_range(
            session, admin.id, range_id, **body.model_dump(exclude_unset=True)
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.delete("/ranges/{range_id}", status_code=204)
async def delete_range(
    range_id: uuid.UUID,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        await svc.delete_range(session, admin.id, range_id)
    except svc.AdminCatalogueError as e:
        _raise(e)


# --- Labs --------------------------------------------------------------


@router.get("/labs", response_model=list[LabResponse])
async def list_labs(
    _admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await svc.list_labs(session)


@router.post("/labs", response_model=LabResponse, status_code=201)
async def create_lab(
    body: LabCreate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.create_lab(session, admin.id, key=body.key, name=body.name)
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.patch("/labs/{lab_id}", response_model=LabResponse)
async def update_lab(
    lab_id: uuid.UUID,
    body: LabUpdate,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_lab(
            session, admin.id, lab_id, **body.model_dump(exclude_unset=True)
        )
    except svc.AdminCatalogueError as e:
        _raise(e)


@router.delete("/labs/{lab_id}", response_model=LabResponse)
async def deactivate_lab(
    lab_id: uuid.UUID,
    admin: Annotated[Account, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        return await svc.update_lab(session, admin.id, lab_id, is_active=False)
    except svc.AdminCatalogueError as e:
        _raise(e)
