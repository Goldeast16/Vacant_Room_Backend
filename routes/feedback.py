from fastapi import APIRouter, Request, status
from models.feedback import FeedbackCreate, FeedbackCreateResult
from zoneinfo import ZoneInfo
from datetime import datetime

router = APIRouter()

COLL_NAME = "feedbacks"

@router.post("/feedback", response_model=FeedbackCreateResult, status_code=status.HTTP_201_CREATED)
async def create_feedback(request: Request, body: FeedbackCreate):
    db = request.app.database
    coll = db[COLL_NAME]

    now = datetime.now(ZoneInfo("Asia/Seoul"))

    # 기본 문서
    doc = {
        "category": body.category,
        "message": body.message,
        "anonymous": body.anonymous,
        "created_at": now,
    }
    if body.page_url is not None:
        doc["page_url"] = body.page_url

    # 익명 아닐 때만 개인정보 저장
    if not body.anonymous:
        if body.email is not None:
            doc["email"] = body.email
        doc["name"] = body.name
        doc["phone"] = body.phone
        doc["privacy_agree"] = True

    result = await coll.insert_one(doc)

    return FeedbackCreateResult(
        id=str(result.inserted_id),
        created_at=now.isoformat()
    )
