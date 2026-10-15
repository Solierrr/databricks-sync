from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Process health, without touching the databases")
def health() -> dict[str, str]:
    return {"status": "ok"}
