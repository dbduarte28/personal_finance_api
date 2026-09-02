import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


def test_create_user_persists(db_session: Session) -> None:
    assert db_session.scalar(select(func.count(User.id))) == 0

    user = User(email="user@example.com", hashed_password="hashed-password")
    db_session.add(user)
    db_session.flush()
    user_id = user.id
    db_session.expire_all()

    persisted_user = db_session.get(User, user_id)

    assert persisted_user is not None
    assert persisted_user.email == "user@example.com"
    assert persisted_user.is_active is True
    assert persisted_user.created_at is not None


def test_duplicate_email_raises(db_session: Session) -> None:
    assert db_session.scalar(select(func.count(User.id))) == 0

    db_session.add(User(email="duplicate@example.com", hashed_password="first-hash"))
    db_session.flush()
    db_session.add(User(email="duplicate@example.com", hashed_password="second-hash"))

    with pytest.raises(IntegrityError):
        db_session.flush()
