from datetime import date, timedelta

import pytest

from repositories import repository
from repositories.repository import FakeRepository
from services import handlers

TOMMOROW = date.today() + timedelta(days=1)


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_commits() -> None:
    repo = repository.FakeRepository.for_batch("b1", "CASEPHONE", 100, None)
    session = FakeSession()

    await handlers.allocate(orderid="o1", sku="CASEPHONE", qty=10, repo=repo, session=session)

    assert session.committed is True


@pytest.mark.asyncio
async def test_returns_allocation() -> None:
    repo = repository.FakeRepository.for_batch("b1", "KEYBOARD", 100, None)
    session = FakeSession()

    result = await handlers.allocate(orderid="o1", sku="KEYBOARD", qty=2, repo=repo, session=session)

    assert result == "b1"


@pytest.mark.asyncio
async def test_error_for_invalid_sku() -> None:
    repo = repository.FakeRepository.for_batch("b1", "AREALSKU", 100, None)
    session = FakeSession()

    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        await handlers.allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10, repo=repo, session=session)


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

    await handlers.add_batch(**batch_data, repo=repo, session=session)
    assert repo.get("b1") is not None
    assert session.committed


# Rewrite domain test against service layer to check that orders are still being allocated
# Still leave all domain tests, they act as a living documentation written in the domain language
@pytest.mark.asyncio
async def test_prefers_warehouse_batches_to_shipments() -> None:
    repo, session = FakeRepository([]), FakeSession()

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

    await handlers.add_batch(**in_stock_batch, repo=repo, session=session)
    await handlers.add_batch(**shipment_batch, repo=repo, session=session)
    await handlers.allocate(orderid="oref", sku="AMPLIFIER", qty=10, repo=repo, session=session)

    assert repo.get("in-stock-batch").available_quantity == 90
    assert repo.get("shipment-batch").available_quantity == 100
