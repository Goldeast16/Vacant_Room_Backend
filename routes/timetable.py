from fastapi import APIRouter, Query
from typing import List, Union, Optional
from pydantic import BaseModel, Field
from db.mongo import get_database

router = APIRouter()

KOR2ENG = {
    "월": "monday", "화": "tuesday", "수": "wednesday",
    "목": "thursday", "금": "friday", "토": "saturday", "일": "sunday"
}
ENG2KOR = {v: k for k, v in KOR2ENG.items()}

class TimetableItem(BaseModel):
    day: str = Field(..., description="요일(한글)")
    start_time: str
    end_time: str
    course_name: str

def _normalize_building(b: Union[int, str]) -> Union[int, str]:
    if isinstance(b, int):
        return b
    s = str(b).strip()
    return int(s) if s.isdigit() else s

@router.get(
    "/api/timetable",
    response_model=List[TimetableItem],
    summary="특정 강의실의 요일별 시간표 조회",
)
async def get_timetable(
    building: Union[int, str] = Query(..., description="건물 번호"),
    room_number: str = Query(..., description="강의실 번호"),
    weekday: str = Query(..., description='요일("월","화","수","목","금","토","일")'),
    limit: Optional[int] = Query(None, ge=1, le=200, description="(옵션) 최대 반환 개수"),
):

    wd = weekday.strip()
    # 요일 입력이 잘못되면 빈 배열 반환
    if wd not in KOR2ENG:
        return []

    day_eng = KOR2ENG[wd]
    bld = _normalize_building(building)
    room = room_number.strip()

    db = get_database()
    coll = db["2025_2_lectures"]

    query = {"building": bld, "room": room, "day": day_eng}
    projection = {"_id": 0, "day": 1, "start_time": 1, "end_time": 1, "course_name": 1}
    cursor = coll.find(query, projection).sort("start_time", 1)
    if limit:
        cursor = cursor.limit(limit)

    docs = await cursor.to_list(length=limit or 1000)

    return [
        TimetableItem(
            day=ENG2KOR.get(d["day"], wd),
            start_time=d["start_time"],
            end_time=d["end_time"],
            course_name=d.get("course_name", ""),
        )
        for d in docs
    ]