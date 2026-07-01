import uuid as _uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.seeds.lab_hierarchy import DEPARTMENTS, test_key_to_department_panel
from app.db.session import get_session
from app.main import app
from app.models import (  # noqa: F401
    Account,
    AccountRole,
    Allergy,
    AuditLog,
    Condition,
    EPIVaccine,
    FamilyHistory,
    Immunization,
    Lab,
    LabDepartment,
    LabPanel,
    LabReferenceRange,
    LabResult,
    LabTestCatalogue,
    LifestyleObservation,
    Medication,
    ObservationType,
    Patient,
    RefreshToken,
    Report,
    Role,
    StoredFile,
)
from app.services.roles import ADMIN_ROLE_KEY, grant_role

_engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# Tables seeded once per session and never written to by any code path
# under test (no admin endpoint mutates them), so they're excluded from
# the per-test TRUNCATE in _clean_tables.
_SEED_TABLES = {
    "epi_vaccines",
    "observation_types",
    "roles",
}

# The lab catalogue hierarchy (departments/panels/tests/ranges) IS
# admin-mutable (Section C). It can't be a one-time session seed like
# the tables above — a test that creates/edits/deactivates a department
# would otherwise leak into every later test. Instead it's truncated and
# re-seeded fresh before every test via _seed_lab_catalogue().

_OBS_TYPE_SEEDS = [
    ("smoking_status", "Smoking Status", "72166-2", "coded", None),
    ("alcohol_use", "Alcohol Use", "74013-4", "coded", None),
    ("exercise", "Physical Activity", "89555-7", "numeric", "min/week"),
    ("sleep_duration", "Sleep Duration", "93832-4", "numeric", "h"),
    ("other", "Other", None, "text", None),
]

_LAB_RANGE_SEEDS = [
    ("fasting_blood_glucose", "general", 70, 100, "mg/dL"),
    ("hba1c", "general", 4.0, 5.6, "%"),
    ("cbc_hemoglobin", "male", 13.5, 17.5, "g/dL"),
    ("cbc_hemoglobin", "female", 12.0, 15.5, "g/dL"),
    ("serum_creatinine", "male", 0.7, 1.3, "mg/dL"),
    ("serum_creatinine", "female", 0.6, 1.1, "mg/dL"),
    ("total_cholesterol", "general", None, 200, "mg/dL"),
    ("tsh", "general", 0.4, 4.0, "mIU/L"),
]

_LAB_CATALOGUE_SEEDS = [
    ("fasting_blood_glucose", "Fasting Blood Glucose", "1558-6", "lab", "blood", "mg/dL"),
    ("hba1c", "HbA1c", "4548-4", "lab", "blood", "%"),
    ("cbc_hemoglobin", "Hemoglobin", "718-7", "lab", "blood", "g/dL"),
    ("serum_creatinine", "Serum Creatinine", "2160-0", "lab", "blood", "mg/dL"),
    ("total_cholesterol", "Total Cholesterol", "2093-3", "lab", "blood", "mg/dL"),
    ("tsh", "Thyroid Stimulating Hormone", "3016-3", "lab", "blood", "mIU/L"),
    ("urinalysis", "Urinalysis", "24356-8", "lab", "urine", None),
    ("chest_xray", "Chest X-Ray", None, "imaging", None, None),
]

_EPI_SEEDS = [
    ("Bacillus Calmette-Guérin", "BCG", 1),
    ("Oral Polio Vaccine", "OPV", 4),
    ("Pentavalent Vaccine", "Penta", 3),
    ("Pneumococcal Conjugate Vaccine", "PCV", 3),
    ("Rotavirus Vaccine", "Rota", 2),
    ("Inactivated Polio Vaccine", "IPV", 2),
    ("Measles Vaccine", "Measles", 2),
    ("Typhoid Conjugate Vaccine", "TCV", 1),
]


async def _seed_lab_catalogue() -> None:
    """(Re-)seed the department/panel/test/range hierarchy. Called once at
    session start and again after every per-test truncation, since this
    hierarchy is admin-mutable and must not leak state between tests.
    """
    async with _session_factory() as sess:
        dept_ids: dict[str, _uuid.UUID] = {}
        panel_ids: dict[tuple[str, str], _uuid.UUID] = {}
        for dept_order, dept in enumerate(DEPARTMENTS):
            did = _uuid.uuid4()
            dept_ids[dept.key] = did
            sess.add(LabDepartment(id=did, key=dept.key, name=dept.name, display_order=dept_order))
            for panel_order, panel in enumerate(dept.panels):
                pid = _uuid.uuid4()
                panel_ids[(dept.key, panel.key)] = pid
                sess.add(
                    LabPanel(
                        id=pid,
                        department_id=did,
                        key=panel.key,
                        name=panel.name,
                        display_order=panel_order,
                    )
                )
        await sess.flush()

        test_key_map = test_key_to_department_panel()
        test_ids: dict[str, _uuid.UUID] = {}
        for key, name, loinc, cat, specimen, unit in _LAB_CATALOGUE_SEEDS:
            tid = _uuid.uuid4()
            test_ids[key] = tid
            dept_key, panel_key = test_key_map[key]
            sess.add(
                LabTestCatalogue(
                    id=tid,
                    key=key,
                    display_name=name,
                    loinc_code=loinc,
                    category=cat,
                    specimen=specimen,
                    default_unit=unit,
                    department_id=dept_ids[dept_key],
                    panel_id=panel_ids[(dept_key, panel_key)] if panel_key else None,
                )
            )
        await sess.flush()

        for test_key, applies, low, high, runit in _LAB_RANGE_SEEDS:
            if test_key in test_ids:
                sess.add(
                    LabReferenceRange(
                        id=_uuid.uuid4(),
                        test_id=test_ids[test_key],
                        applies_to=applies,
                        low=low,
                        high=high,
                        unit=runit,
                    )
                )
        await sess.commit()


@pytest.fixture(scope="session", autouse=True)
async def _setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with _session_factory() as sess:
        for name, short, doses in _EPI_SEEDS:
            sess.add(EPIVaccine(id=_uuid.uuid4(), name=name, short_name=short, total_doses=doses))
        await sess.commit()

    async with _session_factory() as sess:
        for key, label, loinc, vtype, unit in _OBS_TYPE_SEEDS:
            sess.add(
                ObservationType(
                    id=_uuid.uuid4(),
                    key=key,
                    display_label=label,
                    loinc_code=loinc,
                    value_type=vtype,
                    unit=unit,
                )
            )
        await sess.commit()

    async with _session_factory() as sess:
        sess.add(Role(id=_uuid.uuid4(), key=ADMIN_ROLE_KEY, name="Administrator"))
        await sess.commit()

    await _seed_lab_catalogue()

    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables():
    yield
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            if table.name not in _SEED_TABLES:
                await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
    await _seed_lab_catalogue()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as sess:
        yield sess


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        async with _session_factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def registered_user(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def auth_tokens(client: AsyncClient, registered_user: dict) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def admin_auth_tokens(client: AsyncClient) -> dict:
    """A second, distinct account that has been granted admin — via the
    service layer directly with granted_by_account_id=None, exactly
    mirroring the real bootstrap CLI (scripts/grant_admin.py). There is
    no HTTP path that could do this, by design.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 201

    async with _session_factory() as sess:
        await grant_role(
            sess,
            target_email="admin@example.com",
            role_key=ADMIN_ROLE_KEY,
            granted_by_account_id=None,
        )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "securepass123"},
    )
    assert resp.status_code == 200
    return resp.json()
