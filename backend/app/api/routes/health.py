from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="בדיקת תקינות")
def health() -> dict[str, str]:
    return {"status": "ok"}
