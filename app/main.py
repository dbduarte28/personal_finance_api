from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.health import router as health_router
from app.api.routes.summary import router as summary_router
from app.api.routes.transactions import router as transactions_router
from app.api.routes.users import router as users_router

tags_metadata = [
    {
        "name": "Health",
        "description": "Service availability checks.",
    },
    {
        "name": "Authentication",
        "description": "User registration and JWT access token issuance.",
    },
    {
        "name": "Users",
        "description": "Operations for the authenticated user.",
    },
    {
        "name": "Categories",
        "description": "User-owned income and expense category management.",
    },
    {
        "name": "Transactions",
        "description": "User-owned financial transaction management and filtering.",
    },
    {
        "name": "Summary",
        "description": "Aggregated income, expense, balance, and category totals.",
    },
]

app = FastAPI(
    title="Personal Finance API",
    version="1.0.0",
    description=(
        "A REST API for managing user-owned financial categories and transactions, "
        "with JWT authentication and PostgreSQL-powered financial summaries."
    ),
    openapi_tags=tags_metadata,
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(summary_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    errors_without_input = [
        {key: value for key, value in error.items() if key != "input"}
        for error in exception.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(errors_without_input)},
    )
