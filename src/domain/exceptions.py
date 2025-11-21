from dataclasses import dataclass


@dataclass
class OutOfStock(Exception):
    """OutOfStock exception for allocate fn"""

    sku: str
