from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User


@pytest.fixture(autouse=True)
def secure_test_secret(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("SECRET_KEY", "test-only-secret-key-with-32-bytes")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_password_hash_uses_a_random_salt() -> None:
    plain_password = "correct-horse-battery-staple"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != plain_password
    assert second_hash != plain_password
    assert first_hash != second_hash
    assert plain_password not in first_hash
    assert plain_password not in second_hash


def test_verify_password_accepts_only_the_correct_password() -> None:
    hashed_password = hash_password("correct-password")

    assert verify_password("correct-password", hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_plain_password_is_not_stored_returned_or_logged(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    plain_password = "never-store-this-password"
    hashed_password = hash_password(plain_password)
    user = User(email="secure@example.com", hashed_password=hashed_password)
    db_session.add(user)
    db_session.flush()
    db_session.expire_all()

    stored_user = db_session.get(User, user.id)

    assert stored_user is not None
    assert stored_user.hashed_password == hashed_password
    assert stored_user.hashed_password != plain_password
    assert plain_password not in stored_user.hashed_password
    assert plain_password not in caplog.text


def test_access_token_round_trip_returns_subject() -> None:
    token = create_access_token(subject=42)

    assert decode_access_token(token) == 42


def test_expired_access_token_returns_none() -> None:
    token = create_access_token(subject=42, expires_delta=timedelta(seconds=-1))

    assert decode_access_token(token) is None


def test_token_signed_with_another_key_returns_none() -> None:
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "42",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "another-test-secret-key-with-32-bytes",
        algorithm=settings.ALGORITHM,
    )

    assert decode_access_token(token) is None


def test_arbitrary_string_returns_none() -> None:
    assert decode_access_token("this-is-not-a-jwt") is None
