import datetime
from http import HTTPStatus

from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from adapters.pyd_model import OrderLine, Batch
from domain import events, model
from repositories import repository
from services import handlers


def make_app(test_db: Session = None) -> FastAPI:
    app = FastAPI()

    @app.get("/health_check", status_code=HTTPStatus.OK)
    async def health_check() -> dict[str, str]:
        return {"status": "Ok"}


    @app.post("/allocate", status_code=HTTPStatus.ACCEPTED)
    async def allocate_endpoint(
        lines: OrderLine,
    ) -> dict[str, str]:

        line = model.OrderLine(**lines.model_dump())  # pydantic V3.0
        repo = repository.SqlAlchemyRepository(test_db)

        try:
            batchref = await handlers.allocate(line, repo, test_db)
        except (events.OutOfStock, handlers.InvalidSku) as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))
        return {"status": "Ok", "batchref": batchref}


    @app.post("/add_batch", status_code=HTTPStatus.CREATED)
    async def add_batch(batch: Batch) -> dict[str, str]:
        repo = repository.SqlaRepository(test_db)
        try:
            await handlers.add_batch(
                batch=batch, repo=repo, session=test_db
            )
        except handlers.OutOfStockInBatch as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=e.args[0])
        except Exception as e:
            raise  HTTPException(
                HTTPStatus.BAD_REQUEST,
                detail=f"Unhandled exception during query execution: {e.args[0]}"

            )
        return {"status": "Ok"}


    return app
