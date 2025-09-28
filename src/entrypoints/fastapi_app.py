from http import HTTPStatus

from fastapi import FastAPI, HTTPException

from adapters.pyd_model import Batch, OrderLine
from dbschema import orm
from domain import events
from services import handlers, unit_of_work


def make_app() -> FastAPI:
    app = FastAPI()
    orm.start_mappers()

    @app.get("/health_check", status_code=HTTPStatus.OK)
    async def health_check() -> dict[str, str]:
        return {"status": "Ok"}

    @app.post("/allocate", status_code=HTTPStatus.ACCEPTED)
    async def allocate_endpoint(
        lines: OrderLine,
    ) -> dict[str, str]:

        try:
            batchref = await handlers.allocate(
                **lines.model_dump(include={"sku", "qty", "orderid"}),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        except (events.OutOfStock, handlers.InvalidSku) as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))
        return {"status": "Ok", "batchref": batchref}

    @app.post("/add_batch", status_code=HTTPStatus.CREATED)
    async def add_batch(batch: Batch) -> dict[str, str]:

        try:
            await handlers.add_batch(
                **batch.model_dump(include={"reference", "sku", "purchased_quantity", "eta"}),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        except handlers.OutOfStockInBatch as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=e.args[0])
        except Exception as e:
            raise HTTPException(
                HTTPStatus.BAD_REQUEST, detail=f"Unhandled exception during query execution: {e.args[0]}"
            )
        return {"status": "Ok"}

    return app
