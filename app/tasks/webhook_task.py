import logging
import requests
import time
from app.tasks.celery_app import celery

logger = logging.getLogger(__name__)

@celery.task(bind=True, name="app.tasks.webhook_task.send_webhook", autoretry_for=(requests.RequestException,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_webhook(self, url: str, payload: dict, headers: dict = None, timeout: int = 10):
    try:
        start = time.time()
        r = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
        elapsed = time.time() - start
        result = {"status_code": r.status_code, "elapsed": elapsed, "text": r.text[:500]}
        try:
            self.update_state(state="SUCCESS", meta=result)
        except Exception:
            logger.exception("Failed to set success meta for webhook task")
        return result
    except requests.RequestException as exc:
        logger.exception("Webhook POST failed")
        raise