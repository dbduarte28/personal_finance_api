from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionType


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: TransactionType


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: TransactionType | None = None


class CategoryRead(BaseModel):
    id: int
    user_id: int
    name: str
    type: TransactionType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
