from abc import ABC, abstractmethod
from typing import List

from sqlalchemy.orm import Session

from adapters import pyd_model
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
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, batch: Batch) -> None:
        self.session.add(batch)

    def get(self, reference: str) -> Batch:
        return self.session.query(Batch).filter_by(reference=reference).one()

    def list(self) -> List[Batch]:
        """List all batches in the repository."""
        return self.session.query(Batch).all()


class FakeRepository(AbstractRepository):
    def __init__(self, batches) -> None:
        self._batches = set(batches)

    def add(self, batch) -> None:
        self._batches.add(batch)

    def get(self, reference) -> Batch:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> List[Batch]:
        return list(self._batches)

    @staticmethod
    def for_batch(ref, sku, qty, eta=None):
        return FakeRepository([pyd_model.Batch(reference=ref, sku=sku, purchased_quantity=qty, eta=eta)])
