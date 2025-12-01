from pydantic import BaseModel
from typing import List, Optional

class CartItemBase(BaseModel):
    product_id: int
    qty: int

class AddToCartRequest(CartItemBase):
    pass


class CartItemResponse(CartItemBase):
    price_snapshot: float

    class Config:
        orm_mode = True


class CartResponse(BaseModel):
    id: int
    user_id: int
    items: List[CartItemResponse]

    class Config:
        orm_mode = True


# ORDER
class OrderItemResponse(BaseModel):
    product_id: int
    qty: int
    price_snapshot: float

    class Config:
        orm_mode = True


class OrderResponse(BaseModel):
    id: int
    total: float
    status: str   #added after updating in github
    items: List[OrderItemResponse]
    created_at: str

    class Config:
        orm_mode = True

class UpdateOrderStatusRequest(BaseModel):        #added after updating in github
    status: str 