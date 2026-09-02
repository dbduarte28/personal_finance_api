from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud.summary import get_summary
from app.models.user import User
from app.schemas.summary import SummaryRead

router = APIRouter(prefix="/api/v1/summary", tags=["Summary"])


@router.get(
    "",
    response_model=SummaryRead,
    summary="Get a financial summary",
    description=(
        "Aggregate the authenticated user's income, expenses, balance, and category totals, "
        "optionally within an inclusive date range."
    ),
)
def read_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryRead:
    return get_summary(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )
