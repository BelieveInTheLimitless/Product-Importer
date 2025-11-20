from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.tasks.celery_app import celery
from app.database import get_db
from app import crud, schemas
from app.models import Product
from typing import Optional

router = APIRouter()

@router.get("/", response_model=list[schemas.ProductResponse])
def list_products(
    page: int = 1,
    per_page: int = 20,
    search: str = "",
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    if page < 1:
        page = 1
    skip = (page - 1) * per_page
    return crud.get_products(db, skip=skip, limit=per_page, search=search, active=active)

@router.get("/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(404, "Product not found")
    return prod


@router.post("/", response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)

@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    updated = crud.update_product(db, product_id, data)
    if not updated:
        raise HTTPException(404, "Product not found")
    return updated

@router.delete("/delete-all")
def delete_all_products():
    task = celery.send_task("app.tasks.delete_task.delete_all_products")
    return {"task_id": task.id}

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(404, "Product not found")
    return {"message": "Deleted"}