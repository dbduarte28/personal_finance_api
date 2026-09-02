from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class TransactionCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)
    date: date_type


class TransactionUpdate(BaseModel):
    category_id: int | None = None
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )
    description: str | None = Field(default=None, max_length=255)
    date: date_type | None = None


class TransactionRead(BaseModel):
    id: int
    user_id: int
    category_id: int
    amount: Decimal
    description: str | None
    date: date_type
    created_at: datetime
    updated_at: datetime
    category: CategoryRead

    model_config = ConfigDict(from_attributes=True)
