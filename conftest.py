"""Shared pytest fixtures.

Provides an isolated, in-memory SQLite database per test function via a
FastAPI dependency override, so tests never touch the real ``feedhub.db``.
"""
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
from database import Base, get_db
from models import AdminUser
from main import app, pwd_context

# Credentials used by the ``admin_credentials`` fixture.
TEST_ADMIN_USERNAME = "testadmin"
TEST_ADMIN_PASSWORD = "supersecret123"


@pytest_asyncio.fixture
async def session_factory(monkeypatch):
    """Fresh in-memory DB (shared single connection) for one test function."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # The setup-redirect middleware checks admin state via database.AsyncSessionLocal;
    # point it at the test DB so it stays consistent with the dependency override.
    monkeypatch.setattr(database, "AsyncSessionLocal", factory)

    # Default to the DB-backed / setup-wizard path unless a test opts into env creds.
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    yield factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def admin_credentials(session_factory):
    """Insert an admin so the app leaves setup mode; return (username, password)."""
    async with session_factory() as session:
        session.add(
            AdminUser(
                username=TEST_ADMIN_USERNAME,
                password_hash=pwd_context.hash(TEST_ADMIN_PASSWORD),
            )
        )
        await session.commit()
    return TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD
