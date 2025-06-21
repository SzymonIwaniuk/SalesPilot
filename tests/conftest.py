import os
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Generator, Iterable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import clear_mappers, sessionmaker
from sqlalchemy.orm.session import Session
from starlette.testclient import TestClient

from config import get_postgres_uri
from dbschema.orm import metadata, start_mappers
from entrypoints.fastapi_app import make_app


@pytest.fixture
def in_memory_db() -> Engine:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db: Engine) -> Generator[Session, Any, None]:
    start_mappers()
    db_session = sessionmaker(bind=in_memory_db)
    yield db_session()
    clear_mappers()


@pytest.fixture(scope="session")
def postgres_db() -> Engine:
    engine = create_engine(get_postgres_uri())
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session(postgres_db) -> Generator[Session, Any, None]:
    start_mappers()
    pg_session = sessionmaker(bind=postgres_db)
    yield pg_session()
    clear_mappers()


def pytest_addoption(parser) -> None:
    default_url = os.getenv("TEST_SERVER", None) or "http://test"
    parser.addoption("--base-url", action="store", default=default_url, help="Base URL of the API server")


@pytest.fixture
def base_url(request) -> Any:
    return request.config.getoption("--base-url")


# CURRENTLY UNUSED, WORKING AS DOCUMENTATION
@pytest.fixture
def add_stock(postgres_session) -> Generator[Callable[[Iterable], None], Any, None]:
    batches_added = set()
    skus_added = set()

    def add_stock(lines):
        for ref, sku, qty, eta in lines:
            postgres_session.execute(
                text(
                    "INSERT INTO batches (reference, sku, purchased_quantity, eta)" " VALUES (:ref, :sku, :qty, :eta)",
                ),
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )

            [[batch_id]] = postgres_session.execute(
                text(
                    "SELECT id FROM batches WHERE reference = :ref AND sku = :sku",
                ),
                dict(ref=ref, sku=sku),
            )

            batches_added.add(batch_id)
            skus_added.add(sku)

        postgres_session.commit()

    yield add_stock

    for batch_id in batches_added:
        postgres_session.execute(
            text(
                "DELETE FROM allocations WHERE batch_id=:batch_id",
            ),
            dict(batch_id=batch_id),
        )

        postgres_session.execute(
            text(
                "DELETE FROM batches WHERE id=:batch_id",
            ),
            dict(batch_id=batch_id),
        )

        for sku in skus_added:
            postgres_session.execute(
                text(
                    "DELETE FROM order_lines WHERE sku=:sku",
                ),
                dict(sku=sku),
            )

        postgres_session.commit()


@pytest_asyncio.fixture
async def async_test_client(postgres_session, base_url) -> AsyncGenerator[AsyncClient, Any]:
    app = make_app(db_session=postgres_session)
    async with AsyncClient(transport=ASGITransport(app), base_url=base_url) as client:
        yield client


@pytest.fixture
def test_client(postgres_session) -> TestClient:
    app = make_app(db_session=postgres_session)
    return TestClient(app)


@pytest.fixture
def restart_api() -> None:
    (Path(__file__).parent / "fastapi_app.py").touch()
    time.sleep(0.3)
