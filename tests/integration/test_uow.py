from datetime import date

from sqlalchemy import text
from sqlalchemy.orm.session import Session

from adapters import pyd_model


# Helper functions
def insert_batch(session: Session, ref: str, sku: str, qty: int, eta: date) -> None:
    session.execute(
        text("INSERT INTO batches (reference, sku, _purchased_quantity, eta)" "VALUES (:ref, :sku, :qty, :eta)"),
        dict(ref=ref, sku=sku, qty=qty, eta=eta),
    )


def get_allocated_batch_ref(session: Session, orderid: str, sku: str) -> None:
    [[orderlineid]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid=orderid, sku=sku),
    )

    [[batchref]] = session.execute(
        text(
            "SELECT b.reference FROM allocations JOIN batches AS b ON batch_id = b.id" "WHERE orderline_id=:orderlineid"
        ),
        dict(orderlineid=orderid),
    )

    return batchref


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session_factory) -> None:
    session = session_factory()
    insert_batch(session, "batch1", "HIPSTER-WORKBENCH", 100, None)
    session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with uow:
        batch = uow.batches.get(reference="batch1")
        line = pyd_model.OrderLine(orderid="o1", sku="HIPSTER-WORKBENCH", qty=10)
        batch.allocate(line)
        uow.commit()

    batchref = get_allocated_batch_ref(session, "o1", "HIPSTER-WORKBENCH")
    assert batchref == "batch1"
