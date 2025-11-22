from datetime import date, timedelta

import pytest

from domain import events
from domain.model import Batch, OrderLine, Product

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_warehouse_batches_to_shipments() -> None:
    in_stock_batch = Batch("in-stock-batch", "AMPLIFIER", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "AMPLIFIER", 100, eta=tomorrow)
    product = Product(sku="AMPLIFIER", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("oref", "AMPLIFIER", 10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    earliest = Batch("speedy-batch", "MINIMALIST-MICRO", 100, eta=today)
    medium = Batch("normal-batch", "MINIMALIST-MICRO", 100, eta=tomorrow)
    latest = Batch("slow-batch", "MINIMALIST-MICRO", 100, eta=later)
    product = Product(sku="MINIMALIST-MICRO", batches=[medium, earliest, latest])
    line = OrderLine("order1", "MINIMALIST-MICRO", 3)

    product.allocate(line)

    assert earliest.available_quantity == 97
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref() -> None:
    in_stock_batch = Batch("in-stock-batch", "BIG-SPEAKER", 10, eta=None)
    shipment_batch = Batch("shipment-batch-ref", "BIG-SPEAKER", 10, eta=tomorrow)
    product = Product(sku="BIG-SPEAKER", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("oref", "BIG-SPEAKER", 10)

    allocation = product.allocate(line)

    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    batch = Batch("batch1", "SMALL-AMPLIFIER", 10, eta=today)
    product = Product(sku="SMALL-AMPLIFIER", batches=[batch])
    product.allocate(OrderLine("order1", "SMALL-AMPLIFIER", 10))

    allocation = product.allocate(OrderLine("order1", "SMALL-AMPLIFIER", 1))
    assert product.events[-1] == events.OutOfStock(sku="SMALL-AMPLIFIER")
    assert allocation is None


def test_increments_version_number() -> None:
    batch = Batch("b1", "VAPE-PEN", 10, eta=None)
    product = Product(sku="VAPE-PEN", batches=[batch])
    line = OrderLine("order1", "VAPE-PEN", 10)

    product.version_number = 7
    product.allocate(line)

    assert product.version_number == 8
