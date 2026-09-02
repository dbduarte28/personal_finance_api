from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate


def create(
    db: Session,
    user_id: int,
    transaction_data: TransactionCreate,
) -> Transaction:
    transaction = Transaction(user_id=user_id, **transaction_data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def list_by_user(
    db: Session,
    user_id: int,
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    category_id: int | None = None,
    transaction_type: TransactionType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    statement = (
        select(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .options(joinedload(Transaction.category))
        .where(Transaction.user_id == user_id)
    )
    if start_date is not None:
        statement = statement.where(Transaction.date >= start_date)
    if end_date is not None:
        statement = statement.where(Transaction.date <= end_date)
    if category_id is not None:
        statement = statement.where(Transaction.category_id == category_id)
    if transaction_type is not None:
        statement = statement.where(Category.type == transaction_type)

    statement = (
        statement.order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


def get_by_id(
    db: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction | None:
    return db.scalar(
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )


def update(
    db: Session,
    transaction: Transaction,
    transaction_data: TransactionUpdate,
) -> Transaction:
    changes = transaction_data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None or field == "description":
            setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete(db: Session, transaction: Transaction) -> None:
    db.delete(transaction)
    db.commit()
