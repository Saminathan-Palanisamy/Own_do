from pydantic import BaseModel
from datetime import datetime

# -----------------------------------------------------------
class CategoryBase(BaseModel):
    name: str

# -----------------------------------------------------------
class CategoryCreate(CategoryBase):
    pass


# -----------------------------------------------------------
class CategoryUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


# -----------------------------------------------------------
class CategoryResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
