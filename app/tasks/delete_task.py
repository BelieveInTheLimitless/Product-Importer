import logging
from app.tasks.celery_app import celery
from app.database import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="app.tasks.delete_task.delete_all_products")
def delete_all_products_task(self):
    try:
        try:
            self.update_state(state="STARTED", meta={"stage": "started", "message": "Preparing to delete all products"})
        except Exception:
            logger.exception("Failed to set STARTED state for delete task")

        with engine.begin() as conn:
            res = conn.execute(text("DELETE FROM products"))
            deleted = res.rowcount if res is not None else 0

        try:
            self.update_state(state="SUCCESS", meta={"stage": "done", "deleted": deleted})
        except Exception:
            logger.exception("Failed to set SUCCESS meta for delete task")

        return {"deleted": deleted}
    except Exception as exc:
        logger.exception("Failed to delete all products: %s", exc)
        exc_type = type(exc).__name__
        try:
            self.update_state(state="FAILURE", meta={"stage": "error", "exc_type": exc_type, "exc": str(exc)})
        except Exception:
            logger.exception("Could not set FAILURE meta for delete task")
        raise