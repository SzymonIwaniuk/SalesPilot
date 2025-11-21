import pytest

from service_layer import services
from service_layer.unit_of_work import FakeUnitOfWork

# class FakeSession:
#     committed = False
#
#     def commit(self):
#         self.committed = True


@pytest.mark.asyncio
async def test_commits() -> None:
    uow = FakeUnitOfWork()

    await services.add_batch(reference="b1", sku="CASEPHONE", purchased_quantity=100, eta=None, uow=uow)
    await services.allocate(orderid="o1", sku="CASEPHONE", qty=10, uow=uow)

    assert uow.committed is True


@pytest.mark.asyncio
async def test_allocate_returns_allocation() -> None:
    uow = FakeUnitOfWork()
    await services.add_batch(reference="b1", sku="KEYBOARD", purchased_quantity=100, eta=None, uow=uow)
    result = await services.allocate(orderid="o1", sku="KEYBOARD", qty=2, uow=uow)

    assert result == "b1"


@pytest.mark.asyncio
async def test_allocate_error_for_invalid_sku() -> None:
    uow = FakeUnitOfWork()
    await services.add_batch(reference="b1", sku="AREALSKU", purchased_quantity=100, eta=None, uow=uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        await services.allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10, uow=uow)


@pytest.mark.asyncio
async def test_add_batch_for_new_product() -> None:
    uow = FakeUnitOfWork()

    # Also good pattern to create batch pydantic objects using dict with data
    batch_data = {
        "reference": "b1",
        "sku": "FUCKING-BIG-CUP",
        "purchased_quantity": 100,
        "eta": None,
    }

    await services.add_batch(**batch_data, uow=uow)
    product = await uow.products.get("FUCKING-BIG-CUP")
    assert product is not None
    assert uow.committed


@pytest.mark.asyncio
async def test_add_batch_for_existing_product() -> None:
    uow = FakeUnitOfWork()

    await services.add_batch(reference="b1", sku="TABLE", purchased_quantity=100, eta=None, uow=uow)
    await services.add_batch(reference="b2", sku="TABLE", purchased_quantity=99, eta=None, uow=uow)

    assert "b2" in [b.reference for b in (await uow.products.get("TABLE")).batches]
