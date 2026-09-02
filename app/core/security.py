from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import PyJWTError

from app.core.config import get_settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (TypeError, ValueError):
        return False


def create_access_token(subject: int, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    lifetime = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    expires_at = datetime.now(timezone.utc) + lifetime
    payload = {"sub": str(subject), "exp": expires_at}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        subject = payload.get("sub")
        return int(subject) if subject is not None else None
    except (PyJWTError, TypeError, ValueError):
        return None
