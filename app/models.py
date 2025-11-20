from sqlalchemy import Column, String, Integer, Index, func, Boolean, Table, Text
from sqlalchemy.sql import expression
from .database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    active = Column(Boolean, nullable=False, server_default=expression.true())

# Case-insensitive unique index on SKU (Postgres expression index)
Index("ix_products_sku_lower", func.lower(Product.sku), unique=True)


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    url = Column(String, nullable=False)
    event = Column(String, nullable=False, index=True)  # e.g. "product.created", "product.updated", "import.completed"
    enabled = Column(Boolean, nullable=False, server_default=expression.true())
    secret = Column(String, nullable=True)  # optional HMAC secret for signing payloads
    description = Column(Text, nullable=True)
