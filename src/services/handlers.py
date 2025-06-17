from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from adapters.pyd_model import Batch
from domain import model, services
from repositories.repository import AbstractRepository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku: str, batches: List[Batch]) -> bool:
    return sku in {b.sku for b in batches}


async def allocate(orderid: str, sku: str, qty: int, repo: AbstractRepository, session: Session) -> str:
    """
    Allocate a primitive order line to a batch.

    Args:
        orderid: id
        sku: stock-keeping-unit
        qty: quantity
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
    Create from primitives and add batch to the repository and commit the change.

    Args:
        reference:
        sku:
        purchased_quantity:
        eta:
        repo: The repository where the batch will be stored.
        session: The database session for committing the change.

    Returns:
        None
    """

    # TODO Refactor it cuz SQLAlchemy repo take only domain objects
    repo.add(
        model.Batch(
            ref=reference,
            sku=sku,
            qty=purchased_quantity,
            eta=eta,
        )
    )
    session.commit()
