import abc

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import config
from repositories import repository

DEFAULT_ENGINE = create_async_engine(
    config.get_postgres_uri().replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    future=True,
    pool_pre_ping=True,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        "server_settings": {
            "jit": "off", 
            "statement_timeout": "60000", 
            "lock_timeout": "30000", 
            "idle_in_transaction_session_timeout": "60000"  #
        }
    }
)

DEFAULT_SESSION_FACTORY = async_sessionmaker(
    bind=DEFAULT_ENGINE,
    expire_on_commit=False,
    class_=AsyncSession,
    future=True,
    join_transaction_mode="create_savepoint"
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
        try:
            if self.session.in_transaction():
                await self.rollback()
        finally:
            await self.session.close()

    async def commit(self):
        try:
            if self.session.in_transaction():
                await self.session.commit()
        except:
            await self.rollback()
            raise

    async def rollback(self):
        if self.session.in_transaction():
            try:
                await self.session.rollback()
            except:
                await self.session.close()
                raise


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.batches = repository.FakeRepository([])
        self.committed = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass
