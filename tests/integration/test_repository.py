# pylint: disable=protected-access
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.session import Session

from domain.model import Batch, OrderLine
from repositories import repository


@pytest.mark.asyncio
async def test_repository_can_save_a_batch(session: Session) -> None:
    batch = Batch("batch1", "PROFESSIONAL KEYBOARD", 1, eta=None)
    repo = repository.SqlAlchemyRepository(session)
    await repo.add(batch)
    await session.flush()

    rows = await session.execute(text("SELECT reference, sku, purchased_quantity," ' eta FROM "batches"'))
    assert list(rows) == [("batch1", "PROFESSIONAL KEYBOARD", 1, None)]

    await session.rollback()


async def insert_order_line(session: AsyncSession, commit: bool = False) -> int:
    """Insert an order line and return its ID."""
    await session.execute(text("INSERT INTO order_lines (orderid, sku, qty)" ' VALUES ("order1", "EARPADS", 2)'))
    await session.flush()

    result = await session.execute(
        text("SELECT id FROM order_lines WHERE " "orderid=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="EARPADS"),
    )
    [[orderline_id]] = result

    if commit:
        await session.commit()

    return orderline_id


async def insert_batch(session: AsyncSession, batch_id: int, commit: bool = False) -> int:
    """Insert a batch and return its ID."""
    await session.execute(
        text(
            "INSERT INTO batches "
            "(reference, sku, purchased_quantity, eta)"
            ' VALUES (:batch_id, "EARPADS", 2, null)',
        ),
        dict(batch_id=batch_id),
    )
    await session.flush()

    result = await session.execute(
        text("SELECT id FROM batches WHERE " 'reference=:batch_id AND sku="EARPADS"'),
        dict(batch_id=batch_id),
    )
    [[batch_id]] = result

    if commit:
        await session.commit()

    return batch_id


async def insert_allocation(session: AsyncSession, orderline_id: int, batch_id: int) -> None:
    await session.execute(
        text(
            "INSERT INTO allocations (orderline_id, batch_id)" " VALUES (:orderline_id, :batch_id)",
        ),
        dict(orderline_id=orderline_id, batch_id=batch_id),
    )


@pytest.mark.asyncio
async def test_repository_can_retrieve_a_batch_with_allocations(
    session: Session,
) -> None:
    async with session.begin():
        # Set up test data in a transaction
        orderline_id = await insert_order_line(session)
        batch1_id = await insert_batch(session, "batch1")
        await insert_batch(session, "batch2")
        await insert_allocation(session, orderline_id, batch1_id)

        # Test repository get functionality
        repo = repository.SqlAlchemyRepository(session)
        retrieved = await repo.get("batch1")
        expected = Batch("batch1", "EARPADS", 2, eta=None)
        assert retrieved == expected
        assert retrieved.sku == expected.sku
        assert retrieved.purchased_quantity == expected.purchased_quantity
        assert retrieved.eta == expected.eta
        assert retrieved.allocations == {OrderLine("order1", "EARPADS", 2)}
        # Commit to save changes
        await session.commit()


async def get_allocations(session: AsyncSession, batchid: str) -> set:
    result = await session.execute(
        text(
            """
            SELECT orderid
            FROM allocations
            JOIN order_lines ON allocations.orderline_id = order_lines.id
            JOIN batches ON allocations.batch_id = batches.id
            WHERE batches.reference = :batchid
            """,
        ),
        {"batchid": batchid},
    )
    return {row[0] for row in result}


@pytest.mark.asyncio
async def test_updating_a_batch(session: AsyncSession):
    batch = Batch("batch1", "MOUSE", 2, eta=None)
    repo = repository.SqlAlchemyRepository(session)
    await repo.add(batch)

    batch.purchased_quantity = 3
    await repo.update(batch)

    rows = await session.execute(text("SELECT reference, sku, purchased_quantity," ' eta FROM "batches"'))
    assert list(rows) == [("batch1", "MOUSE", 3, None)]

    await session.rollback()
