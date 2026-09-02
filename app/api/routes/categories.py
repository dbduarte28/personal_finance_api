from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import category as category_crud
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/api/v1/categories", tags=["Categories"])


def category_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Category not found",
    )


def category_conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A category with this name already exists",
    )


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    description="Create an income or expense category owned by the authenticated user.",
)
def create_category(
    category_data: CategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CategoryRead:
    try:
        return category_crud.create(db, current_user.id, category_data)
    except IntegrityError as error:
        db.rollback()
        raise category_conflict() from error


@router.get(
    "",
    response_model=list[CategoryRead],
    summary="List categories",
    description="List the authenticated user's categories with limit/offset pagination.",
)
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CategoryRead]:
    return category_crud.list_by_user(db, current_user.id, limit, offset)


@router.get(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Get a category",
    description="Return a category owned by the authenticated user.",
)
def read_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CategoryRead:
    category = category_crud.get_by_id(db, category_id, current_user.id)
    if category is None:
        raise category_not_found()
    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryRead,
    summary="Update a category",
    description="Update the name or type of a category owned by the authenticated user.",
)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CategoryRead:
    category = category_crud.get_by_id(db, category_id, current_user.id)
    if category is None:
        raise category_not_found()

    try:
        return category_crud.update(db, category, category_data)
    except IntegrityError as error:
        db.rollback()
        raise category_conflict() from error


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
    description="Delete an owned category when it is not referenced by a transaction.",
)
def delete_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    category = category_crud.get_by_id(db, category_id, current_user.id)
    if category is None:
        raise category_not_found()

    try:
        category_crud.delete(db, category)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category cannot be deleted because it has transactions",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
