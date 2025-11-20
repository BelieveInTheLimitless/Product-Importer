# app/main.py
import os
import time
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.exc import OperationalError

from app.api.products import router as products_router
from app.api.uploads import router as uploads_router
from app.api.webhooks import router as webhooks_router
from app.database import Base, engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Product Importer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    logger.warning("Static directory not found at %s", static_dir)

app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])


@app.on_event("startup")
def startup_migrate_and_check_db():
    retries = int(os.getenv("DB_STARTUP_RETRIES", "8"))
    delay = float(os.getenv("DB_STARTUP_DELAY", "2.0"))

    for attempt in range(1, retries + 1):
        try:
            logger.info("DB init attempt %s/%s", attempt, retries)
            Base.metadata.create_all(bind=engine)
            logger.info("DB tables ready")
            break
        except OperationalError as e:
            logger.warning("DB not ready (attempt %s/%s): %s", attempt, retries, e)
            if attempt == retries:
                logger.error("Exceeded DB init retries (%s). Continuing without tables.", retries)
                break
            time.sleep(delay)
            delay = min(delay * 1.5, 10.0)


@app.get("/", include_in_schema=False)
def serve_ui():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    logger.warning("index.html not found at %s; returning API message", index_path)
    return {"message": "Product API running"}