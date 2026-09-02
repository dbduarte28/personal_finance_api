from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import category as category_crud
from app.crud import transaction as transaction_crud
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


def transaction_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transaction not found",
    )


def ensure_category_belongs_to_user(
    db: Session,
    category_id: int,
    user_id: int,
) -> None:
    if category_crud.get_by_id(db, category_id, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transaction",
    description="Create a transaction in a category owned by the authenticated user.",
)
def create_transaction(
    transaction_data: TransactionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TransactionRead:
    ensure_category_belongs_to_user(db, transaction_data.category_id, current_user.id)
    return transaction_crud.create(db, current_user.id, transaction_data)


@router.get(
    "",
    response_model=list[TransactionRead],
    summary="List transactions",
    description=(
        "List the authenticated user's transactions with optional date, category, and type "
        "filters plus limit/offset pagination."
    ),
)
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: date_type | None = None,
    end_date: date_type | None = None,
    category_id: int | None = None,
    transaction_type: Annotated[
        TransactionType | None,
        Query(alias="type"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TransactionRead]:
    return transaction_crud.list_by_user(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        transaction_type=transaction_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Get a transaction",
    description="Return a transaction owned by the authenticated user.",
)
def read_transaction(
    transaction_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TransactionRead:
    transaction = transaction_crud.get_by_id(db, transaction_id, current_user.id)
    if transaction is None:
        raise transaction_not_found()
    return transaction


@router.patch(
    "/{transaction_id}",
    response_model=TransactionRead,
    summary="Update a transaction",
    description="Update fields on a transaction owned by the authenticated user.",
)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TransactionRead:
    transaction = transaction_crud.get_by_id(db, transaction_id, current_user.id)
    if transaction is None:
        raise transaction_not_found()

    if transaction_data.category_id is not None:
        ensure_category_belongs_to_user(
            db,
            transaction_data.category_id,
            current_user.id,
        )
    return transaction_crud.update(db, transaction, transaction_data)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
    description="Delete a transaction owned by the authenticated user.",
)
def delete_transaction(
    transaction_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    transaction = transaction_crud.get_by_id(db, transaction_id, current_user.id)
    if transaction is None:
        raise transaction_not_found()
    transaction_crud.delete(db, transaction)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
