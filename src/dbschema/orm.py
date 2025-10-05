from sqlalchemy import (Column, Date, ForeignKey, Integer, MetaData, String,
                        Table)
from sqlalchemy.orm import class_mapper, registry, relationship

from domain.model import Batch, OrderLine

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
    Column("sku", String(255)),
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


def start_mappers():
    try:
        class_mapper(OrderLine)
    except:
        lines_mapper = mapper_registry.map_imperatively(OrderLine, order_lines)

        mapper_registry.map_imperatively(
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
