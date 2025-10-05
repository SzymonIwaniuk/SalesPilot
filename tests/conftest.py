import asyncio
import os
import time
from pathlib import Path
from typing import AsyncGenerator, Callable, Generator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import clear_mappers

from config import get_postgres_uri
from dbschema.orm import metadata, start_mappers
from domain.model import Batch
from entrypoints.fastapi_app import make_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def orm_mappers():
    """Session-scoped fixture to manage SQLAlchemy mapper lifecycle."""
    start_mappers()
    yield
    clear_mappers()


@pytest_asyncio.fixture(scope="session")
async def test_app(orm_mappers, event_loop) -> FastAPI:
    """Create FastAPI app for testing."""

    asyncio.set_event_loop(event_loop)
    app = make_app()
    return app


@pytest_asyncio.fixture
async def async_test_client(test_app, event_loop) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Get a test client instance that automatically follows redirects."""

    asyncio.set_event_loop(event_loop)

    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
        follow_redirects=True,
    )
    client.headers.update({"Content-Type": "application/json"})
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def in_memory_db(orm_mappers) -> Engine:
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
    )
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def postgres_db(orm_mappers, event_loop) -> AsyncGenerator[Engine, None]:
    """Get a PostgreSQL database for testing."""
    engine = create_async_engine(
        get_postgres_uri(),
    )

    try:
        async with engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        yield engine
    finally:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(metadata.drop_all)
        finally:
            await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(in_memory_db: Engine):
    """Create a session factory for SQLite testing."""
    return async_sessionmaker(
        bind=in_memory_db, expire_on_commit=False, autoflush=True, future=True, class_=AsyncSession
    )


@pytest_asyncio.fixture
async def postgres_session_factory(postgres_db: Engine):
    """Create a session factory for PostgreSQL testing."""
    return async_sessionmaker(
        bind=postgres_db,
    )


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Get a SQLite session for testing."""
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def postgres_session(postgres_session_factory, event_loop) -> AsyncGenerator[AsyncSession, None]:
    """Get a PostgreSQL session for testing."""
    session = postgres_session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
async def add_stock(postgres_session: AsyncSession) -> AsyncGenerator[Callable[[list[tuple]], None], None]:
    """Add stock batches to the database using the ORM.

    Args:
        lines: List of tuples (reference, sku, quantity, eta)
    """
    batches_to_delete = []

    async def add_stock(lines: list[tuple]) -> None:
        async with postgres_session.begin():
            for ref, sku, qty, eta in lines:
                batch = Batch(ref, sku, qty, eta)
                postgres_session.add(batch)
                batches_to_delete.append(batch)

    yield add_stock

    try:
        async with postgres_session.begin():
            for batch in batches_to_delete:
                await postgres_session.delete(batch)
    except Exception:
        pass


def pytest_addoption(parser) -> None:
    """Add custom pytest command line options."""
    default_url = os.getenv("TEST_SERVER", "http://test")
    parser.addoption("--base-url", action="store", default=default_url, help="base url of the api server")


@pytest.fixture
def base_url(request) -> str:
    """Get the base URL for API testing."""
    return request.config.getoption("--base-url")


@pytest.fixture
def restart_api() -> None:
    """Touch the FastAPI app file to trigger reload in development."""
    (Path(__file__).parent / "../src/entrypoints/fastapi_app.py").touch()
    time.sleep(0.5)
