from abc import ABC, abstractmethod
from typing import Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain import model
from domain.model import Product


class AbstractRepository(ABC):
    """Abstract base class for batch repositories.

    This class defines the interface for repository implementations that handle
    storage and retrieval of Batch entities. Subclasses must implement methods
    to add, get

    Methods:
        add(batch: Batch):
            Adds a Batch instance to the repository.
        get(reference: str) -> Batch:
            Retrieves a Batch by its unique reference.
    """

    def __init__(self) -> None:
        self.seen: Set[Product] = set()

    async def add(self, product: Product) -> None:
        await self._add(product)
        self.seen.add(product)

    async def get(self, sku: str) -> Product:
        product = await self._get(sku)
        if product:
            self.seen.add(product)
        return product

    @abstractmethod
    async def _add(self, product: Product) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _get(self, sku: str) -> Product:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def _add(self, product: Product) -> None:
        self.session.add(product)
        await self.session.flush()

    async def _get(self, sku: str) -> Product:
        result = await self.session.execute(
            select(model.Product)
            .filter_by(sku=sku)
            .options(selectinload(model.Product.batches).selectinload(model.Batch.allocations))
        )
        return result.scalar_one_or_none()


class FakeRepository(AbstractRepository):
    def __init__(self, products) -> None:
        super().__init__()
        self._products = set(products)

    async def _add(self, product) -> None:
        self._products.add(product)

    async def _get(self, sku) -> Product:
        return next((p for p in self._products if p.sku == sku), None)
