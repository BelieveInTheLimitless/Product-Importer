from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy import or_
from app import models, schemas

def get_products(db: Session, skip: int = 0, limit: int = 20, search: str = "", active: bool | None = None):
    query = db.query(models.Product)

    if search:
        wildcard = f"%{search.lower()}%"
        query = query.filter(
            or_(
                models.Product.sku.ilike(wildcard),
                models.Product.name.ilike(wildcard),
                models.Product.description.ilike(wildcard)
            )
        )

    if active is not None:
        query = query.filter(models.Product.active == active)

    return query.order_by(models.Product.id.desc()).offset(skip).limit(limit).all()

def get_by_sku_ci(db: Session, sku: str):
    return db.query(models.Product).filter(func.lower(models.Product.sku) == sku.lower()).first()


def create_product(db: Session, product: schemas.ProductCreate):
    existing = get_by_sku_ci(db, product.sku)
    if existing:
        existing.name = product.name
        existing.description = product.description
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    db_product = models.Product(
        sku=product.sku,
        name=product.name,
        description=product.description
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, data: schemas.ProductUpdate):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()

    if not product:
        return None

    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if hasattr(data, "active") and data.active is not None:
        product.active = data.active

    db.commit()
    db.refresh(product)
    return product



def delete_product(db: Session, product_id: int):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return None

    db.delete(product)
    db.commit()
    return product


def create_webhook(db: Session, webhook_in: schemas.WebhookCreate) -> models.Webhook:
    db_wh = models.Webhook(
        name=webhook_in.name,
        url=str(webhook_in.url),
        event=webhook_in.event,
        enabled=webhook_in.enabled if webhook_in.enabled is not None else True,
        secret=webhook_in.secret,
        description=webhook_in.description,
    )
    db.add(db_wh)
    db.commit()
    db.refresh(db_wh)
    return db_wh

def get_webhooks(db: Session, skip: int = 0, limit: int = 100, event: Optional[str] = None):
    q = db.query(models.Webhook)
    if event:
        q = q.filter(models.Webhook.event == event)
    return q.order_by(models.Webhook.id.desc()).offset(skip).limit(limit).all()

def get_webhook(db: Session, webhook_id: int) -> Optional[models.Webhook]:
    return db.query(models.Webhook).filter(models.Webhook.id == webhook_id).first()

def update_webhook(db: Session, webhook_id: int, data: schemas.WebhookUpdate):
    wh = get_webhook(db, webhook_id)
    if not wh:
        return None
    if data.name is not None:
        wh.name = data.name
    if data.url is not None:
        wh.url = str(data.url)
    if data.event is not None:
        wh.event = data.event
    if data.enabled is not None:
        wh.enabled = data.enabled
    if data.secret is not None:
        wh.secret = data.secret
    if data.description is not None:
        wh.description = data.description
    db.commit()
    db.refresh(wh)
    return wh

def delete_webhook(db: Session, webhook_id: int):
    wh = get_webhook(db, webhook_id)
    if not wh:
        return None
    db.delete(wh)
    db.commit()
    return wh