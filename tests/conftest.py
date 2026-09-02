import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


TEST_ENVIRONMENT = {
    "APP_NAME": "Personal Finance API",
    "ENVIRONMENT": "test",
    "DATABASE_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/personal_finance",
    "TEST_DATABASE_URL": (
        "postgresql+psycopg://postgres:postgres@localhost:5432/personal_finance_test"
    ),
    "SECRET_KEY": "test-only-secret-key-with-32-bytes",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
}
for key, value in TEST_ENVIRONMENT.items():
    os.environ.setdefault(key, value)

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app import models as app_models  # noqa: E402, F401


test_engine = create_engine(get_settings().TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(test_database: None) -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    credentials = {
        "email": "authenticated@example.com",
        "password": "secure-password",
    }
    register_response = client.post("/api/v1/auth/register", json=credentials)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": credentials["email"], "password": credentials["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
