import uuid as _uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import (  # noqa: F401
    Account,
    Allergy,
    AuditLog,
    Condition,
    EPIVaccine,
    FamilyHistory,
    Immunization,
    LifestyleObservation,
    Medication,
    ObservationType,
    Patient,
    RefreshToken,
)

_engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_SEED_TABLES = {"epi_vaccines", "observation_types"}

_OBS_TYPE_SEEDS = [
    ("smoking_status", "Smoking Status", "72166-2", "coded", None),
    ("alcohol_use", "Alcohol Use", "74013-4", "coded", None),
    ("exercise", "Physical Activity", "89555-7", "numeric", "min/week"),
    ("sleep_duration", "Sleep Duration", "93832-4", "numeric", "h"),
    ("other", "Other", None, "text", None),
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


@pytest.fixture(scope="session", autouse=True)
async def _setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with _session_factory() as sess:
        result = await sess.execute(text("SELECT count(*) FROM epi_vaccines"))
        if result.scalar_one() == 0:
            for name, short, doses in _EPI_SEEDS:
                sess.add(
                    EPIVaccine(id=_uuid.uuid4(), name=name, short_name=short, total_doses=doses)
                )
            await sess.commit()

    async with _session_factory() as sess:
        result = await sess.execute(text("SELECT count(*) FROM observation_types"))
        if result.scalar_one() == 0:
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
