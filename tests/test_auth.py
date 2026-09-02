from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.crud.user import get_by_email

USER_DATA = {
    "email": "user@example.com",
    "password": "secure-password",
}


def register_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=USER_DATA)
    assert response.status_code == 201


def test_register_valid_user(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/auth/register", json=USER_DATA)

    assert response.status_code == 201
    assert response.json()["email"] == USER_DATA["email"]
    assert response.json()["is_active"] is True
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()
    assert USER_DATA["password"] not in response.text

    stored_user = get_by_email(db_session, USER_DATA["email"])
    assert stored_user is not None
    assert stored_user.hashed_password != USER_DATA["password"]
    assert verify_password(USER_DATA["password"], stored_user.hashed_password)


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    register_user(client)

    response = client.post("/api/v1/auth/register", json=USER_DATA)

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "secure-password"},
        {"email": "user@example.com", "password": "x7$Qz"},
    ],
)
def test_register_validates_email_and_password(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert all("input" not in error for error in response.json()["detail"])
    assert payload["password"] not in response.text


def test_login_with_correct_credentials_returns_token(client: TestClient) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": USER_DATA["email"], "password": USER_DATA["password"]},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert decode_access_token(response.json()["access_token"]) is not None
    assert USER_DATA["password"] not in response.text


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (USER_DATA["email"], "wrong-password"),
        ("missing@example.com", USER_DATA["password"]),
    ],
)
def test_login_with_invalid_credentials_returns_401(
    client: TestClient,
    email: str,
    password: str,
) -> None:
    register_user(client)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )

    assert response.status_code == 401
    assert password not in response.text


def test_users_me_with_valid_token(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["email"] == "authenticated@example.com"
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()


def test_users_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_users_me_with_invalid_signature_returns_401(client: TestClient) -> None:
    settings = get_settings()
    token = jwt.encode(
        {"sub": "1"},
        "another-test-secret-key-with-32-bytes",
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_users_me_with_expired_token_returns_401(client: TestClient) -> None:
    token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_inactive_user_returns_401(client: TestClient, db_session: Session) -> None:
    register_user(client)
    user = get_by_email(db_session, USER_DATA["email"])
    assert user is not None
    user.is_active = False
    db_session.commit()
    token = create_access_token(user.id)

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
