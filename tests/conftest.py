from typing import AsyncGenerator, Callable

from httpx import AsyncClient, ASGITransport
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_postgres_uri
from dbschema.orm import metadata
from domain.model import Batch
from entrypoints.fastapi_app import make_app
from typing import Final

TEST_BASE_URL: Final[str] = "http://test"
IN_MEMORY_DB_URI: Final[str] = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def test_app() -> FastAPI:
    app = make_app()
    return app

@pytest_asyncio.fixture
async def async_test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url=TEST_BASE_URL,
    ) as ac:
        yield ac
    await ac.aclose()


@pytest_asyncio.fixture
async def in_memory_db() -> Engine:
    engine = create_async_engine(
        IN_MEMORY_DB_URI,
    )
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def postgres_db() -> AsyncGenerator[Engine, None]:
    engine = create_async_engine(
        get_postgres_uri(),
    )

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(in_memory_db: Engine):
    return async_sessionmaker(
        bind=in_memory_db,
    )


@pytest_asyncio.fixture
async def postgres_session_factory(postgres_db: Engine):
    return async_sessionmaker(
        bind=postgres_db,
    )


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    session = session_factory()
    yield session
    await session.close()


@pytest_asyncio.fixture
async def postgres_session(postgres_session_factory) -> AsyncGenerator[AsyncSession, None]:
    session = postgres_session_factory()
    yield session
    await session.close()


@pytest_asyncio.fixture
async def add_stock(postgres_session: AsyncSession) -> AsyncGenerator[Callable[[list[tuple]], None], None]:
    batches_to_delete = []

    async def add_stock(lines: list[tuple]) -> None:
        async with postgres_session.begin():
            for ref, sku, qty, eta in lines:
                batch = Batch(ref, sku, qty, eta)
                postgres_session.add(batch)
                batches_to_delete.append(batch)

    yield add_stock

    async with postgres_session.begin():
        for batch in batches_to_delete:
            await postgres_session.delete(batch)
