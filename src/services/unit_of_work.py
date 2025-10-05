import abc

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

import config
from repositories import repository

DEFAULT_ENGINE = create_async_engine(
    config.get_postgres_uri().replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    future=True,
    pool_pre_ping=True,
)

DEFAULT_SESSION_FACTORY = async_sessionmaker(
    bind=DEFAULT_ENGINE,
    expire_on_commit=False,
    class_=AsyncSession,
)


class AbstractUnitOfWork(abc.ABC):
    batches: repository.AbstractRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.rollback()

    @abc.abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory(future=True, join_transaction_mode="create_savepoint")
        self.batches = repository.SqlAlchemyRepository(self.session)
        await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def commit(self):
        await self.session.commit()
  
    async def rollback(self):
        await self.session.rollback()


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.batches = repository.FakeRepository([])
        self.committed = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass
