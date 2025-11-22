import abc

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import config
from repositories import repository
from service_layer import messagebus

DEFAULT_ENGINE = create_async_engine(
    config.get_postgres_uri(),
)

DEFAULT_SESSION_FACTORY = async_sessionmaker(
    bind=DEFAULT_ENGINE,
)


class AbstractUnitOfWork(abc.ABC):
    products: repository.AbstractRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.rollback()

    async def commit(self):
        await self._commit()
        self.publish_events()

    def publish_events(self):
        for product in self.products.seen:
            print(vars(product))
            while product.events:
                event = product.events.pop(0)
                messagebus.handle(event)

    @abc.abstractmethod
    async def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.products = repository.SqlAlchemyRepository(self.session)
        await self.session.begin()
        return await super().__aenter__()

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self.session.close()

    async def _commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self.products = repository.FakeRepository([])
        self.committed = False

    async def _commit(self):
        self.committed = True

    async def rollback(self):
        pass
