from http import HTTPStatus

from fastapi import FastAPI, HTTPException

from adapters.pyd_model import Batch, OrderLine
from dbschema import orm
from domain import events
from services import handlers, unit_of_work
from functools import lru_cache

@lru_cache(maxsize=1)
def setup_mappers() -> None:
    """Setup SQLAlchemy ORM mappers - called only once."""
    orm.start_mappers()

def make_app() -> FastAPI:
    app = FastAPI()

    setup_mappers()

    @app.get("/health_check", status_code=HTTPStatus.OK)
    async def health_check() -> dict[str, str]:
        return {"status": "Ok"}

    @app.post("/allocate", status_code=HTTPStatus.ACCEPTED)
    async def allocate_endpoint(
        lines: OrderLine,
    ) -> dict[str, str]:
        try:
            async with unit_of_work.SqlAlchemyUnitOfWork() as uow:
                batchref = await handlers.allocate(
                    **lines.model_dump(include={"sku", "qty", "orderid"}),
                    uow=uow,
                )
                await uow.commit()
            return {"status": "Ok", "batchref": batchref}
        except (events.OutOfStock, handlers.InvalidSku) as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))
        except Exception as e:
            print(f"Error in allocate_endpoint: {str(e)}")
            raise HTTPException(HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e))

    @app.post("/add_batch", status_code=HTTPStatus.CREATED)
    async def add_batch(batch: Batch) -> dict[str, str]:
        try:
            async with unit_of_work.SqlAlchemyUnitOfWork() as uow:
                await handlers.add_batch(
                    **batch.model_dump(include={"reference", "sku", "purchased_quantity", "eta"}),
                    uow=uow,
                )
                await uow.commit()
            return {"status": "Ok"}
        except handlers.OutOfStockInBatch as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))

    return app
