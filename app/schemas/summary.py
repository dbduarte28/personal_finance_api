from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import TransactionType


class CategorySummary(BaseModel):
    name: str
    type: TransactionType
    total: Decimal


class SummaryRead(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    by_category: list[CategorySummary]
