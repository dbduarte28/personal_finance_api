from datetime import date
from decimal import Decimal
from sqlalchemy import Numeric, case, func, literal, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.summary import CategorySummary, SummaryRead

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def get_summary(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> SummaryRead:
    filters = [Transaction.user_id == user_id]
    if start_date is not None:
        filters.append(Transaction.date >= start_date)
    if end_date is not None:
        filters.append(Transaction.date <= end_date)

    zero = literal(ZERO, type_=Numeric(12, 2))
    total_income = func.coalesce(
        func.sum(
            case(
                (Category.type == TransactionType.INCOME, Transaction.amount),
                else_=zero,
            )
        ),
        zero,
    )
    total_expense = func.coalesce(
        func.sum(
            case(
                (Category.type == TransactionType.EXPENSE, Transaction.amount),
                else_=zero,
            )
        ),
        zero,
    )

    totals_statement = (
        select(
            total_income.label("total_income"),
            total_expense.label("total_expense"),
        )
        .select_from(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(*filters)
    )
    totals = db.execute(totals_statement).one()

    categories_statement = (
        select(
            Category.name,
            Category.type,
            func.sum(Transaction.amount).label("total"),
        )
        .select_from(Transaction)
        .join(Category, Category.id == Transaction.category_id)
        .where(*filters)
        .group_by(Category.id, Category.name, Category.type)
        .order_by(Category.name, Category.id)
    )
    categories = db.execute(categories_statement).all()

    income = _money(totals.total_income)
    expense = _money(totals.total_expense)

    return SummaryRead(
        total_income=income,
        total_expense=expense,
        balance=_money(income - expense),
        by_category=[
            CategorySummary(
                name=category.name,
                type=category.type,
                total=_money(category.total),
            )
            for category in categories
        ],
    )
