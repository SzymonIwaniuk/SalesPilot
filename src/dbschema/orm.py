from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, String, Table, event
from sqlalchemy.orm import registry, relationship
from sqlalchemy.sql import text

from domain.model import Batch, OrderLine, Product

mapper_registry = registry()
metadata = MetaData()


order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer),
    Column("orderid", String(255)),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", ForeignKey("products.sku")),
    Column("purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("OrderLine_id", ForeignKey("order_lines.id", ondelete="CASCADE")),
    Column("batch_id", ForeignKey("batches.id", ondelete="CASCADE")),
)

products = Table(
    "products",
    metadata,
    Column("sku", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, server_default=text("0")),
)


def start_mappers():
    lines_mapper = mapper_registry.map_imperatively(OrderLine, order_lines)

    batches_mapper = mapper_registry.map_imperatively(
        Batch,
        batches,
        properties={
            "allocations": relationship(
                lines_mapper,
                secondary=allocations,
                collection_class=set,
                cascade="all, delete",
                passive_deletes=True,
            )
        },
    )

    mapper_registry.map_imperatively(Product, products, properties={"batches": relationship(batches_mapper)})


# tells SQLALchemy whenever a Product object is loaded from the db, call this function and init product.events
@event.listens_for(Product, "load")
def receive_load(product, _):
    product.events = []
