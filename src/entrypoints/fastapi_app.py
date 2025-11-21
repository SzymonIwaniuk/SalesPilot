from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, HTTPException

from adapters.pyd_model import Batch, OrderLine
from dbschema import orm
from domain import exceptions
from service_layer import services, unit_of_work

orm.start_mappers()


@asynccontextmanager
async def create_tables(app: FastAPI):
    async with unit_of_work.DEFAULT_ENGINE.begin() as conn:
        await conn.run_sync(orm.metadata.create_all)
    yield


def make_app() -> FastAPI:

    app = FastAPI(lifespan=create_tables)

    @app.get("/health_check", status_code=HTTPStatus.OK)
    async def health_check() -> dict[str, str]:
        return {"status": "Ok"}

    @app.post("/allocate", status_code=HTTPStatus.ACCEPTED)
    async def allocate_endpoint(
        line: OrderLine,
    ) -> dict[str, str]:
        try:
            uow = unit_of_work.SqlAlchemyUnitOfWork()
            batchref = await services.allocate(
                **line.model_dump(include={"sku", "qty", "orderid"}),
                uow=uow,
            )
        except (exceptions.OutOfStock, services.InvalidSku) as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))

        return {"status": "Ok", "batchref": batchref}


    @app.post("/add_batch", status_code=HTTPStatus.CREATED)
    async def add_batch(batch: Batch) -> dict[str, str]:
        try:
            uow = unit_of_work.SqlAlchemyUnitOfWork()
            await services.add_batch(
                    **batch.model_dump(include={"reference", "sku", "purchased_quantity", "eta"}),
                    uow=uow,
            )
        except services.OutOfStockInBatch as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))

        return {"status": "Ok"}

    return app
