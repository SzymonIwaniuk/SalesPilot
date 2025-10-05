from abc import ABC, abstractmethod
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from domain.model import Batch
from domain import model


class AbstractRepository(ABC):
    """Abstract base class for batch repositories.

    This class defines the interface for repository implementations that handle 
    storage and retrieval of Batch entities. Subclasses must implement methods 
    to add, get, update, and list batches.

    Methods:
        add(batch: Batch):
            Adds a Batch instance to the repository.
        get(reference: str) -> Batch:
            Retrieves a Batch by its unique reference.
        update(batch: Batch):
            Updates a Batch instance in the repository.
        list() -> List[Batch]:
            Lists all batches in the repository.
    """

    @abstractmethod
    async def add(self, batch: Batch) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, reference: str) -> Batch:
        raise NotImplementedError
        
    @abstractmethod
    async def update(self, batch: Batch) -> None:
        raise NotImplementedError
        
    @abstractmethod
    async def list(self) -> List[Batch]:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, batch: Batch) -> None:
        self.session.add(batch)
        await self.session.flush()

    async def get(self, reference: str) -> Batch:
        result = await self.session.execute(
            select(model.Batch).filter_by(reference=reference).options(selectinload(model.Batch.allocations))
        )
        return result.scalar_one_or_none()

    async def list(self) -> List[Batch]:
        result = await self.session.execute(
            select(Batch).options(selectinload(Batch.allocations))
        )
        return list(result.scalars().all())


    async def update(self, batch: Batch) -> None:
        await self.session.flush()
        

class FakeRepository(AbstractRepository):
    def __init__(self, batches) -> None:
        self._batches = set(batches)

    async def add(self, batch) -> None:
        self._batches.add(batch)

    async def get(self, reference) -> Batch:
        try:
            return next(b for b in self._batches if b.reference == reference)
        except StopIteration:
            raise KeyError(f"Batch with reference {reference} not found")

    async def list(self) -> List[Batch]:
        return list(self._batches)

    async def update(self, batch: Batch) -> None:
        pass
    
    @staticmethod
    def for_batch(ref, sku, qty, eta=None):
        return FakeRepository([model.Batch(reference=ref, sku=sku, purchased_quantity=qty, eta=eta)])
