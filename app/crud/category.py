from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def create(db: Session, user_id: int, category_data: CategoryCreate) -> Category:
    category = Category(user_id=user_id, **category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_by_user(
    db: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[Category]:
    statement = (
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


def get_by_id(db: Session, category_id: int, user_id: int) -> Category | None:
    return db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    )


def update(
    db: Session,
    category: Category,
    category_data: CategoryUpdate,
) -> Category:
    for field, value in category_data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    ).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
