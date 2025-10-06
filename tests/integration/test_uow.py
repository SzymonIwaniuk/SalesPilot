from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain import model
from services import unit_of_work


# Helper functions
async def insert_batch(session: AsyncSession, ref: str, sku: str, qty: int, eta: date, product_version=1) -> None:
    await session.execute(
        text("INSERT INTO products (sku, version_number)" "VALUES (:sku, :version)"),
        dict(sku=sku, version=product_version),
    )
    await session.execute(
        text("INSERT INTO batches (reference, sku, purchased_quantity, eta)" "VALUES (:ref, :sku, :qty, :eta)"),
        dict(ref=ref, sku=sku, qty=qty, eta=eta),
    )


async def get_allocated_batch_ref(session: AsyncSession, orderid: str, sku: str) -> None:
    result = await session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid=orderid, sku=sku),
    )
    [[orderlineid]] = result

    result = await session.execute(
        text(
            "SELECT b.reference FROM allocations JOIN batches AS b ON batch_id = b.id"
            " "
            "WHERE orderline_id=:orderlineid"
        ),
        dict(orderlineid=orderlineid),
    )
    [[batchref]] = result

    return batchref


@pytest.mark.asyncio
async def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory) -> None:
    session = session_factory()
    await insert_batch(session, "batch1", "HIPSTER-WORKBENCH", 100, None)
    await session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    async with uow:
        product = await uow.products.get(sku="HIPSTER-WORKBENCH")
        line = model.OrderLine(orderid="o1", sku="HIPSTER-WORKBENCH", qty=10)
        product.allocate(line)
        await uow.commit()

    batchref = await get_allocated_batch_ref(session, "o1", "HIPSTER-WORKBENCH")
    assert batchref == "batch1"


@pytest.mark.asyncio
async def test_rolls_back_uncommitted_work_by_default(session_factory) -> None:
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    async with uow:
        await insert_batch(uow.session, "batch1", "MEDIUM-PLINTH", 100, None)

    new_session = session_factory()
    result = await new_session.execute(text("SELECT * FROM batches"))
    rows = list(result)
    assert rows == []


@pytest.mark.asyncio
async def test_rolls_back_on_error(session_factory) -> None:
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(MyException):
        async with uow:
            await insert_batch(uow.session, "batch1", "LARGE-FORK", 100, None)
            raise MyException()

    new_session = session_factory()
    result = await new_session.execute(text("SELECT * FROM batches"))
    rows = list(result)
    assert rows == []
