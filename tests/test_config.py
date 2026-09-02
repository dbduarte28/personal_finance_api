from app.core.config import get_settings


def test_settings_read_from_env(monkeypatch) -> None:
    environment = {
        "APP_NAME": "Test Personal Finance API",
        "ENVIRONMENT": "test",
        "DATABASE_URL": "postgresql+psycopg://test:test@db/test",
        "TEST_DATABASE_URL": "postgresql+psycopg://test:test@db/test_database",
        "SECRET_KEY": "test-secret-key",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.APP_NAME == "Test Personal Finance API"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15

    get_settings.cache_clear()
