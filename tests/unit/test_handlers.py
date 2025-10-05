from datetime import date, timedelta

import pytest

from services import handlers
from services.unit_of_work import FakeUnitOfWork

TOMMOROW = date.today() + timedelta(days=1)


# class FakeSession:
#     committed = False
#
#     def commit(self):
#         self.committed = True


@pytest.mark.asyncio
async def test_commits() -> None:
    uow = FakeUnitOfWork()

    await handlers.add_batch(reference="b1", sku="CASEPHONE", purchased_quantity=100, eta=None, uow=uow)
    await handlers.allocate(orderid="o1", sku="CASEPHONE", qty=10, uow=uow)

    assert uow.committed is True


@pytest.mark.asyncio
async def test_returns_allocation() -> None:
    uow = FakeUnitOfWork()
    await handlers.add_batch(reference="b1", sku="KEYBOARD", purchased_quantity=100, eta=None, uow=uow)
    result = await handlers.allocate(orderid="o1", sku="KEYBOARD", qty=2, uow=uow)

    assert result == "b1"


@pytest.mark.asyncio
async def test_error_for_invalid_sku() -> None:
    uow = FakeUnitOfWork()
    await handlers.add_batch(reference="b1", sku="AREALSKU", purchased_quantity=100, eta=None, uow=uow)

    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        await handlers.allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10, uow=uow)


@pytest.mark.asyncio
async def test_add_batch() -> None:
    uow = FakeUnitOfWork()

    # Also good pattern to create batch pydantic objects using dict with data
    batch_data = {
        "reference": "b1",
        "sku": "FUCKING-BIG-CUP",
        "purchased_quantity": 100,
        "eta": None,
    }

    await handlers.add_batch(**batch_data, uow=uow)
    batch = await uow.batches.get("b1")
    assert batch is not None
    assert uow.committed


# Rewrite domain test against service layer to check that orders are still being allocated
# Still leave all domain tests, they act as a living documentation written in the domain language
@pytest.mark.asyncio
async def test_prefers_warehouse_batches_to_shipments() -> None:
    uow = FakeUnitOfWork()

    in_stock_batch = {
        "reference": "in-stock-batch",
        "sku": "AMPLIFIER",
        "purchased_quantity": 100,
        "eta": None,
    }

    shipment_batch = {
        "reference": "shipment-batch",
        "sku": "AMPLIFIER",
        "purchased_quantity": 100,
        "eta": TOMMOROW,
    }

    await handlers.add_batch(**in_stock_batch, uow=uow)
    await handlers.add_batch(**shipment_batch, uow=uow)
    await handlers.allocate(orderid="oref", sku="AMPLIFIER", qty=10, uow=uow)

    in_stock = await uow.batches.get("in-stock-batch")
    shipment = await uow.batches.get("shipment-batch")

    assert in_stock.available_quantity == 90
    assert shipment.available_quantity == 100
