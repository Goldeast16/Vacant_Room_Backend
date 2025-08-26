from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse, JSONResponse
from models.feedback import FeedbackCreate, FeedbackCreateResult
from zoneinfo import ZoneInfo
from datetime import datetime
from io import BytesIO
from typing import List, Dict, Any
from utils.excel import make_feedback_excel

router = APIRouter()

COLL_NAME = "feedbacks"
KST = ZoneInfo("Asia/Seoul")

@router.post("/feedback", response_model=FeedbackCreateResult, status_code=status.HTTP_201_CREATED)
async def create_feedback(request: Request, body: FeedbackCreate):
    db = request.app.database
    coll = db[COLL_NAME]

    now = datetime.now(KST)

    # 기본 문서
    doc: Dict[str, Any] = {
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

@router.get("/feedback/export")
async def export_feedback(request: Request):
    """
    모든 피드백을 Excel 파일로 다운로드.
    성공: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    실패(데이터 없음): 404 + {"message": "No feedback data"}
    """
    db = request.app.database
    coll = db[COLL_NAME]

    docs: List[Dict[str, Any]] = await coll.find({}).sort("created_at", 1).to_list(None)

    if not docs:
        return JSONResponse({"message": "No feedback data"}, status_code=404)

    wb = make_feedback_excel(docs)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f'feedback_export_{datetime.now(KST).strftime("%Y%m%d_%H%M%S")}.xlsx'
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
    )