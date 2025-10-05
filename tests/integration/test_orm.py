from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from domain import model
from domain.model import Batch, OrderLine


@pytest.mark.asyncio
async def test_orderline_mapper_can_load_lines(session) -> None:
    await session.execute(
        text(
            "INSERT INTO order_lines (orderid, sku, qty) VALUES "
            '("order1", "HEADPHONES", 1),'
            '("order2", "MOUSE", 2),'
            '("order3", "FLASH", 3)'
        )
    )

    expected = [
        OrderLine("order1", "HEADPHONES", 1),
        OrderLine("order2", "MOUSE", 2),
        OrderLine("order3", "FLASH", 3),
    ]
    result = await session.execute(select(OrderLine))
    assert list(result.scalars().all()) == expected

    await session.rollback()


@pytest.mark.asyncio
async def test_orderline_mapper_can_save_lines(session) -> None:
    new_line = OrderLine("order1", "DECORATIVE-LEDS", 3)
    session.add(new_line)
    await session.flush()

    result = await session.execute(text('SELECT orderid, sku, qty FROM "order_lines"'))
    rows = list(result)
    assert rows == [("order1", "DECORATIVE-LEDS", 3)]

    await session.rollback()


@pytest.mark.asyncio
async def test_retrieving_batches(session) -> None:
    await session.execute(
        text("INSERT INTO batches (reference, sku, purchased_quantity, eta)" ' VALUES ("batch1", "sku1", 100, null)')
    )

    await session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            ' VALUES ("batch2", "sku2", 200, "2025-05-21")'
        )
    )
    await session.flush()

    expected = [
        Batch("batch1", "sku1", 100, eta=None),
        Batch("batch2", "sku2", 200, eta=date(2025, 5, 21)),
    ]

    result = await session.execute(select(Batch))
    assert list(result.scalars().all()) == expected

    await session.rollback()


@pytest.mark.asyncio
async def test_saving_batches(session) -> None:
    batch = Batch("batch1", "sku1", 100, eta=None)
    session.add(batch)
    await session.flush()

    result = await session.execute(text('SELECT reference, sku, purchased_quantity, eta FROM "batches"'))
    rows = list(result)

    assert rows == [("batch1", "sku1", 100, None)]

    await session.rollback()


@pytest.mark.asyncio
async def test_saving_allocations(session) -> None:
    batch = Batch("batch1", "sku1", 100, eta=None)
    line = OrderLine("order1", "sku1", 10)
    batch.allocate(line)
    session.add(batch)
    await session.flush()

    result = await session.execute(text('SELECT orderline_id, batch_id FROM "allocations"'))
    rows = list(result)

    assert rows == [(line.id, batch.id)]

    await session.rollback()


@pytest.mark.asyncio
async def test_retrieving_allocations(session) -> None:
    # Insert order line
    await session.execute(text('INSERT INTO order_lines (orderid, sku, qty) VALUES ("order1", "sku1", 12)'))
    await session.flush()

    # Get order line ID
    result = await session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="sku1"),
    )
    [[olid]] = result

    # Insert batch
    await session.execute(
        text("INSERT INTO batches (reference, sku, purchased_quantity, eta) " 'VALUES ("batch1", "sku1", 100, null)')
    )

    # Get batch ID
    result = await session.execute(
        text("SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
        dict(ref="batch1", sku="sku1"),
    )
    [[bid]] = result

    # Insert allocation
    await session.execute(
        text("INSERT INTO allocations (OrderLine_id, batch_id) VALUES (:olid, :bid)"),
        dict(olid=olid, bid=bid),
    )

    # Query and verify
    result = await session.execute(select(Batch).options(selectinload(model.Batch.allocations)))
    batch = result.scalar_one()
    assert batch.allocations == {OrderLine("order1", "sku1", 12)}

    await session.rollback()
