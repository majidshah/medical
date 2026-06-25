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
from app.models import Account, AuditLog, RefreshToken  # noqa: F401

_engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def _setup_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables():
    yield
    async with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
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
