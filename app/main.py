from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.products import router as products_router
from app.api.uploads import router as uploads_router
from app.api.webhooks import router as webhooks_router
from app.database import Base, engine
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])

@app.get("/")
def root():
    return {"message": "Product API running"}