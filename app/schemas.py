from pydantic import BaseModel, HttpUrl
from typing import Optional

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True

class WebhookBase(BaseModel):
    name: Optional[str] = None
    url: HttpUrl
    event: str  # e.g. "product.created", "import.completed"
    enabled: Optional[bool] = True
    secret: Optional[str] = None
    description: Optional[str] = None

class WebhookCreate(WebhookBase):
    pass

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    event: Optional[str] = None
    enabled: Optional[bool] = None
    secret: Optional[str] = None
    description: Optional[str] = None

class WebhookResponse(WebhookBase):
    id: int

    class Config:
        from_attributes = True
