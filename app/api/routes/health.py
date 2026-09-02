from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Check service health",
    description="Return a simple availability response for the API service.",
)
def health() -> dict[str, str]:
    return {"status": "ok"}
