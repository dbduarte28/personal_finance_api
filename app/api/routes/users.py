from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get the current user",
    description="Return the profile associated with the supplied bearer token.",
)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
