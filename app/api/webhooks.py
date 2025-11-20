from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas
import time
import requests

router = APIRouter()

@router.post("/", response_model=schemas.WebhookResponse)
def create_webhook(webhook: schemas.WebhookCreate, db: Session = Depends(get_db)):
    return crud.create_webhook(db, webhook)

@router.get("/", response_model=list[schemas.WebhookResponse])
def list_webhooks(skip: int = 0, limit: int = 100, event: str = "", db: Session = Depends(get_db)):
    return crud.get_webhooks(db, skip, limit, event or None)

@router.get("/{webhook_id}", response_model=schemas.WebhookResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = crud.get_webhook(db, webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook not found")
    return wh

@router.put("/{webhook_id}", response_model=schemas.WebhookResponse)
def update_webhook(webhook_id: int, data: schemas.WebhookUpdate, db: Session = Depends(get_db)):
    updated = crud.update_webhook(db, webhook_id, data)
    if not updated:
        raise HTTPException(404, "Webhook not found")
    return updated

@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_webhook(db, webhook_id)
    if not deleted:
        raise HTTPException(404, "Webhook not found")
    return {"message": "Deleted"}

@router.post("/{webhook_id}/test")
def test_webhook(webhook_id: int, payload: dict = {}, db: Session = Depends(get_db)):
    wh = crud.get_webhook(db, webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook not found")

    if not wh.enabled:
        raise HTTPException(400, "Webhook is disabled")

    start = time.time()
    try:
        r = requests.post(wh.url, json=payload or {"test": True, "event": wh.event}, timeout=10)
        duration = time.time() - start
        return {"status_code": r.status_code, "elapsed": duration, "text": r.text[:200]}
    except requests.RequestException as exc:
        duration = time.time() - start
        raise HTTPException(status_code=502, detail=f"Request failed: {str(exc)} (elapsed {duration:.2f}s)")