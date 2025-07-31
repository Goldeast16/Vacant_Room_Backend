from fastapi import APIRouter
from typing import Optional
from db.mongo import get_database
from utils.time_utils import calculate_minutes_diff, format_minutes_to_string
from pymongo import ASCENDING
from collections import defaultdict
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

SOON_THRESHOLD = 60  # 분 단위
DEFAULT_AVAILABLE_MINUTES = 9999


def lecture_to_dict(lec):
    if lec is None:
        return None
    return {
        "course_name": lec.get("course_name"),
        "start_time": lec.get("start_time"),
        "end_time": lec.get("end_time"),
        "professor": lec.get("professor")
    }


def extract_floor(room: str) -> str:
    match = re.match(r"(B?\d+)", room)
    if not match:
        return "?"
    prefix = match.group(1)
    return prefix[:2] if prefix.startswith("B") else prefix[:-2]


def determine_room_status(target_time: str, next_lecture, current_lecture):
    if current_lecture:
        return "in_use", 0, None
    elif next_lecture:
        minutes = calculate_minutes_diff(target_time, next_lecture["start_time"])
        status = "soon" if minutes <= SOON_THRESHOLD else "empty"
        msg = f"{format_minutes_to_string(minutes)} 후 다음 수업이 시작됩니다"
        return status, minutes, msg
    else:
        return "empty", DEFAULT_AVAILABLE_MINUTES, None


@router.get("/rooms")
async def get_rooms(
    building: str,
    hour: int,
    minute: int,
    weekday: str,
    floor: Optional[str] = None,
):
    db = get_database()
    target_time = f"{hour:02d}:{minute:02d}"

    day_eng = weekday_map.get(weekday)
    if not day_eng:
        return {"error": "잘못된 요일 형식입니다. (월~일 중 하나를 입력해주세요)"}

    query = {"building": int(building), "day": day_eng}
    if floor:
        query["room"] = {"$regex": f"^{floor}"}

    cursor = db["2025_2_lectures"].find(query).sort("start_time", ASCENDING)
    lectures = await cursor.to_list(length=None)

    rooms_dict = defaultdict(list)
    for lec in lectures:
        rooms_dict[lec["room"]].append(lec)

    response = []

    for room, room_lectures in rooms_dict.items():
        current = None
        next_lectures = []

        for lec in room_lectures:
            if lec["start_time"] <= target_time < lec["end_time"]:
                current = lec
            elif lec["start_time"] > target_time:
                next_lectures.append(lec)

        next_lecture = next_lectures[0] if next_lectures else None
        status, available_minutes, soon_message = determine_room_status(target_time, next_lecture, current)

        response.append({
            "building": building,
            "floor": extract_floor(room),
            "room_number": room,
            "status": status,
            "current_lecture": lecture_to_dict(current),
            "next_lecture": lecture_to_dict(next_lecture),
            "next_lectures": [lecture_to_dict(lec) for lec in next_lectures],
            "available_minutes": available_minutes,
            "soon_message": soon_message,
        })

    return response
