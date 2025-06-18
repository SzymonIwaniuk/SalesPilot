from __future__ import annotations

from datetime import date
from typing import Optional, Set
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from domain import model
from domain.model import OrderId, Quantity, Reference, Sku


class OrderLine(BaseModel, model.OrderLine):
    """Pydantic adapter for domain OrderLine model."""

    sku: Sku
    qty: Quantity
    orderid: OrderId
    id: Optional[UUID] = Field(default=None, exclude=True)

    def __hash__(self) -> int:
        data = self.model_dump()
        return hash((data["sku"], data["qty"], data["orderid"]))  # use dump_model before hashing, fix problems with orm

    def __eq__(self, other) -> bool:
        if not isinstance(other, OrderLine):
            return False

        return all(
            (
                other.orderid == self.orderid,
                other.sku == self.sku,
                other.qty == self.qty,
            )
        )

    model_config = ConfigDict(
        from_attributes=True,
        frozen=True,
        json_schema_extra={
            "example": {
                "id": "12345678123456781234567812345678",
                "sku": "SONY-HEADPHONES",
                "qty": 1,
                "orderid": "order-123",
            }
        },
    )


class OrderLineWithAllocatedIn(model.OrderLine):
    allocated_in: Batch


class Batch(BaseModel, model.Batch):
    """Pydantic adapter for domain Batch model."""

    id: Optional[UUID] = Field(default=None, exclude=True)
    reference: Reference
    sku: Sku
    eta: Optional[date]
    purchased_quantity: Quantity
    allocations: Set[OrderLine] = Field(default_factory=set)

    def __hash__(self) -> int:
        return hash(self.reference)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "12345678123456781234567812345678",
                "reference": "batch-001",
                "sku": "SONY-HEADPHONES",
                "purchased_quantity": 1,
                "eta": "2025-06-18",
                "allocations": [
                    {
                        "id": "12345678123456781234567812345678",
                        "orderid": "order-123",
                        "sku": "SONY-HEADPHONES",
                        "qty": 1,
                    }
                ],
            }
        },
    )
