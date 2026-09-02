from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.crud import user as user_crud
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/auth")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> UserRead:
    if user_crud.get_by_email(db, str(user_data.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    try:
        return user_crud.create(db, user_data)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from error


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = user_crud.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(
        access_token=create_access_token(user.id),
        token_type="bearer",
    )
