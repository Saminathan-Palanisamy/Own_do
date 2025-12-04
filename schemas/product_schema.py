from typing import List, Optional
from pydantic import BaseModel


class ProductImageBase(BaseModel):
    image_url: str


class ProductImageResponse(ProductImageBase):
    id: int

    class Config:
        orm_mode = True


# ---------------------------------------
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int


class ProductCreate(ProductBase):
    image_urls: List[str] = []  


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_urls: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: int
    category_id: int
    is_active: bool
    images: List[ProductImageResponse]

    class Config:
        orm_mode = True
