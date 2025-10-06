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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_postgres_uri
from dbschema.orm import metadata
from domain.model import Batch
from entrypoints.fastapi_app import make_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_app(event_loop) -> FastAPI:
    asyncio.set_event_loop(event_loop)
    app = make_app()
    return app


@pytest_asyncio.fixture
async def async_test_client(test_app, event_loop) -> AsyncGenerator[httpx.AsyncClient, None]:
    asyncio.set_event_loop(event_loop)

    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=test_app),
        base_url="http://test",
        follow_redirects=True,
    )
    client.headers.update({"Content-Type": "application/json"})
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def in_memory_db() -> Engine:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
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


def pytest_addoption(parser) -> None:
    default_url = os.getenv("TEST_SERVER", "http://test")
    parser.addoption("--base-url", action="store", default=default_url, help="base url of the api server")


@pytest.fixture
def base_url(request) -> str:
    return request.config.getoption("--base-url")


@pytest.fixture
def restart_api() -> None:
    (Path(__file__).parent / "../src/entrypoints/fastapi_app.py").touch()
    time.sleep(0.5)
