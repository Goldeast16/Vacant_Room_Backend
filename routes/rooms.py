from fastapi import APIRouter
from typing import Optional
from db.mongo import get_database
from utils.time_utils import calculate_minutes_diff, format_minutes_to_string
from pymongo import ASCENDING
import re

router = APIRouter()

weekday_map = {
    "월": "monday",
    "화": "tuesday",
    "수": "wednesday",
    "목": "thursday",
    "금": "friday",
    "토": "saturday",
    "일": "sunday",
}

def lecture_to_dict(lec):
    return {
        "course_name": lec["course_name"],
        "start_time": lec["start_time"],
        "end_time": lec["end_time"],
        "professor": lec["professor"]
    }

def extract_floor(room: str) -> str:

    match = re.match(r"(B?\d+)", room)
    if match:
        prefix = match.group(1)
        # 숫자만 있는 경우: 앞자리만 층
        if prefix.startswith("B"):
            return prefix[:2]  # B3, B2 등
        else:
            return prefix[:-2]  # 602 → 6
    return "?"

@router.get("/rooms")
async def get_rooms(
    building: str,
    hour: int,
    minute: int,
    weekday: str,
    floor: Optional[str] = None,  # ✅ str로 변경
):
    db = get_database()
    target_time = f"{hour:02d}:{minute:02d}"

    # 1. 건물 + 요일 필터
    day_eng = weekday_map.get(weekday)
    if not day_eng:
        return {"error": "잘못된 요일 형식입니다. (월~일 중 하나를 입력해주세요)"}

    query = {"building": int(building), "day": day_eng}
    if floor is not None:
        query["room"] = {"$regex": f"^{floor}"}

    cursor = db["2025_2_lectures"].find(query).sort("start_time", ASCENDING)
    lectures = await cursor.to_list(length=None)

    rooms_dict = {}
    for lec in lectures:
        room = lec["room"]
        if room not in rooms_dict:
            rooms_dict[room] = []
        rooms_dict[room].append(lec)

    response = []

    for room, room_lectures in rooms_dict.items():
        current = None
        next_lectures = []
        next_lecture = None

        for lec in room_lectures:
            if lec["start_time"] <= target_time < lec["end_time"]:
                current = lec
            elif lec["start_time"] > target_time:
                next_lectures.append(lec)

        if next_lectures:
            next_lecture = next_lectures[0]

        if current:
            status = "in_use"
            available_minutes = 0
            soon_message = None
        elif next_lecture:
            minutes = calculate_minutes_diff(target_time, next_lecture["start_time"])
            status = "soon" if minutes <= 60 else "empty"
            available_minutes = minutes
            soon_message = f"{format_minutes_to_string(minutes)} 후 다음 수업이 시작됩니다"
        else:
            status = "empty"
            available_minutes = 9999
            soon_message = None

        response.append({
            "building": building,
            "floor": extract_floor(room),
            "room_number": room,
            "status": status,
            "current_lecture": lecture_to_dict(current) if current else None,
            "next_lecture": lecture_to_dict(next_lecture) if next_lecture else None,
            "next_lectures": [lecture_to_dict(lec) for lec in next_lectures],
            "available_minutes": available_minutes,
            "soon_message": soon_message,
        })

    return response
