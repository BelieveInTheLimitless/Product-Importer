import os
import logging
import importlib
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL, 
)

celery.conf.update(
    task_track_started=True,
    result_expires=3600,      
    accept_content=["json"],      
    task_serializer="json",
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

TASK_MODULES = [
    "app.tasks.import_task",
    "app.tasks.delete_task",
    "app.tasks.webhook_task",
]

for mod in TASK_MODULES:
    try:
        importlib.import_module(mod)
        logger.info("Imported Celery tasks module: %s", mod)
    except Exception as exc:
        logger.warning("Failed importing tasks module %s: %s", mod, exc)
