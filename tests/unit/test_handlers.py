from datetime import date, timedelta

import pytest
from markdown_it.rules_block import reference

from adapters import pyd_model
from repositories import repository
from repositories.repository import FakeRepository
from services import handlers

TOMMOROW = date.today() + timedelta(days=1)


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_commits():
    line = pyd_model.OrderLine(orderid="o1", sku="CASEPHONE", qty=10)
    batch = pyd_model.Batch(reference="b1", sku="CASEPHONE", purchased_quantity=100, eta=None)
    repo = repository.FakeRepository([batch])
    session = FakeSession()

    await handlers.allocate(line, repo, session)
    assert session.committed is True


@pytest.mark.asyncio
async def test_returns_allocations() -> None:
    line = pyd_model.OrderLine(orderid="o1", sku="KEYBOARD", qty=2)
    batch = pyd_model.Batch(reference="b1", sku="KEYBOARD", purchased_quantity=100, eta=None)
    repo = repository.FakeRepository([batch])

    result = await handlers.allocate(line, repo, FakeSession())
    assert result == "b1"


@pytest.mark.asyncio
async def test_error_for_invalid_sku() -> None:
    line = pyd_model.OrderLine(orderid="o1", sku="NONEXISTENTSKU", qty=10)
    batch = pyd_model.Batch(reference="b1", sku="AREALSKU", purchased_quantity=100, eta=None)
    repo = repository.FakeRepository([batch])

    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        await handlers.allocate(line, repo, FakeSession())


# Rewrite domain test against service layer to check that orders are still being allocated
# Still leave all domain tests, they act as a living documentation written in the domain language
@pytest.mark.asyncio
async def test_prefers_warehouse_batches_to_shipments() -> None:
    in_stock_batch = pyd_model.Batch(reference="in-stock-batch", sku="AMPLIFIER", purchased_quantity=100, eta=None)
    shipment_batch = pyd_model.Batch(reference="shipment-batch", sku="AMPLIFIER", purchased_quantity=100, eta=TOMMOROW)
    repo = repository.FakeRepository([in_stock_batch, shipment_batch])
    session = FakeSession()

    line = pyd_model.OrderLine(orderid="oref", sku="AMPLIFIER", qty=10)

    await handlers.allocate(line, repo, session)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


@pytest.mark.asyncio
async def test_add_batch() -> None:
    repo, session = FakeRepository([]), FakeSession()

    # Also good pattern to create batch pydantic objects using dict with data
    batch_data = {
        "reference": "b1",
        "sku": "FUCKING-BIG-CUP",
        "purchased_quantity": 100,
        "eta": None,
    }

    batch = pyd_model.Batch(**batch_data)
    await handlers.add_batch(batch, repo, session)
    assert repo.get("b1") is not None
    assert session.committed
