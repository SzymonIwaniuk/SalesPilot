from typing import List

from domain.exceptions import OutOfStock
from domain.model import Batch, OrderLine


def allocate(line: OrderLine, batches: List[Batch]) -> str:
    """
    Allocate an order line to the first batch that can fulfill it.

    This function attempts to allocate the given order line to the earliest
    batch that has sufficient quantity available. Batches are assumed to be
    sorted by arrival time (ETA), with in-stock batches prioritized.

    Args:
        line (OrderLine): The order line to allocate.
        batches (List[Batch]): A list of available batches to consider for allocation

    Returns:
        str: The reference of the batch that was allocated.

    Raises:
        OutOfStock: If no batch can fulfill the order line.
    """

    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
        return batch.reference

    except StopIteration:
        raise OutOfStock(f"Out of stock for sku {line.sku}")
