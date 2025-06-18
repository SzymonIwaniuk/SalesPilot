from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from adapters.pyd_model import Batch
from domain import model, services
from repositories.repository import AbstractRepository


class InvalidSku(Exception):
    """Raised when an invalid sku is encountered in /allocate route"""
    pass


class OutOfStockInBatch(Exception):
    """Raised when encountered error in /add_batch route"""
    pass


def is_valid_sku(sku: str, batches: List[Batch]) -> bool:
    """Check whether a sku is valid"""
    return sku in {b.sku for b in batches}


async def allocate(orderid: str, sku: str, qty: int, repo: AbstractRepository, session: Session) -> str:
    """
    Create from primitives order line and allocate it to a batch.

    Args:
        orderid: Unique order id
        sku: Stock-keeping-unit
        qty: Quantity
        repo: The repository to fetch available batches.
        session: The database session for committing changes.

    Raises:
        InvalidSku: If the sku in the order line is not valid.

    Returns:
        str: The reference id of the batch to which the order line was allocated.
    """

    line = model.OrderLine(orderid, sku, qty)
    batches = repo.list()

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")

    batchref = services.allocate(line, batches)
    session.commit()
    return batchref


async def add_batch(
    reference: str,
    sku: str,
    purchased_quantity: int,
    eta: Optional[date],
    repo: AbstractRepository,
    session: Session,
) -> None:
    """
    Creates a new `Batch` instance from primitive values,
    adds it to the repository and commits the changes.

    Args:
        reference: Unique reference code for the batch.
        sku: Stock Keeping Unit identifying the product.
        purchased_quantity: Total quantity purchased in this batch.
        eta: Estimated time of arrival for the batch. Can be `None`.
        repo: The repository where the batch will be stored.
        session: The database session for committing the change.

    Returns:
        None
    """

    repo.add(
        model.Batch(
            ref=reference,
            sku=sku,
            qty=purchased_quantity,
            eta=eta,
        )
    )
    session.commit()
