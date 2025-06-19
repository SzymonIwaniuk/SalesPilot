from abc import ABC, abstractmethod
from typing import List, Any, Sequence

from sqlalchemy import Row, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from domain.model import Batch


class AbstractRepository(ABC):
    """
    Abstract base class for batch repositories.

    Defines the interface for repository implementations that handle storage
    and retrieval of Batch entities.

    Subclasses must implement methods to add a batch, get a batch by its
    reference, and list all batches.

    Methods:
        add(batch: Batch) -> None:
            Add a Batch instance to the repository.

        get(reference: str) -> Batch:
            Retrieve a Batch by its unique reference.
    """

    @abstractmethod
    async def add(self, batch: Batch) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, reference: str) -> Batch:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, batch: Batch) -> None:
        self.session.add(batch)
        await self.session.flush()

    async def get(self, reference: str) -> Batch:
        result = await self.session.execute(
            select(Batch).filter_by(reference=reference)
        )
        return result.scalars().one()

    async def list(self) -> Sequence[Row[Any] | RowMapping | Any]:
        """List all batches in the repository."""
        result = await self.session.execute(select(Batch))
        return result.scalars().all()


class FakeRepository(AbstractRepository):
    def __init__(self, batches) -> None:
        self._batches = set(batches)

    def add(self, batch) -> None:
        self._batches.add(batch)

    def get(self, reference) -> Batch:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> List[Batch]:
        return list(self._batches)
