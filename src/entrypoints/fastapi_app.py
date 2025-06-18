from http import HTTPStatus

from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from adapters.pyd_model import Batch, OrderLine
from domain import events
from repositories import repository
from services import handlers


def make_app(db_session: Session) -> FastAPI:
    app = FastAPI()

    @app.get("/health_check", status_code=HTTPStatus.OK)
    async def health_check() -> dict[str, str]:
        return {"status": "Ok"}

    @app.post("/allocate", status_code=HTTPStatus.ACCEPTED)
    async def allocate_endpoint(
        lines: OrderLine,
    ) -> dict[str, str]:

        repo = repository.SqlAlchemyRepository(db_session)

        try:
            batchref = await handlers.allocate(
                **lines.model_dump(include={"sku", "qty", "orderid"}), repo=repo, session=db_session
            )
        except (events.OutOfStock, handlers.InvalidSku) as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=str(e))
        return {"status": "Ok", "batchref": batchref}

    @app.post("/add_batch", status_code=HTTPStatus.CREATED)
    async def add_batch(batch: Batch) -> dict[str, str]:
        repo = repository.SqlAlchemyRepository(db_session)
        try:
            await handlers.add_batch(
                **batch.model_dump(include={"reference", "sku", "purchased_quantity", "eta"}),
                repo=repo,
                session=db_session,
            )
        except handlers.OutOfStockInBatch as e:
            raise HTTPException(HTTPStatus.BAD_REQUEST, detail=e.args[0])
        except Exception as e:
            raise HTTPException(
                HTTPStatus.BAD_REQUEST, detail=f"Unhandled exception during query execution: {e.args[0]}"
            )
        return {"status": "Ok"}

    return app
