from fastapi import APIRouter, Request
from pymongo.errors import PyMongoError

health_router = APIRouter()

@health_router.get("/health")
@health_router.head("/health")  # HEAD 요청도 허용
async def health_check(request: Request):
    db_status = "unknown"

    try:
        result = await request.app.database.command("ping")
        db_status = "ok" if result.get("ok") == 1 else "fail"
    except (AttributeError, PyMongoError):
        db_status = "fail"

    return {
        "status": "ok",
        "mongodb": db_status,
        "version": "1.0.0"
    }
