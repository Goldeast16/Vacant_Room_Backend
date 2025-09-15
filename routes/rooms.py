from fastapi import APIRouter
from typing import Optional, List, Dict, Any
from db.mongo import get_database
from utils.time_utils import calculate_minutes_diff, format_minutes_to_string
from pymongo import ASCENDING
from collections import defaultdict
import re

router = APIRouter()

# 한글 요일 → 영문 매핑
weekday_map = {
    "월": "monday",
    "화": "tuesday",
    "수": "wednesday",
    "목": "thursday",
    "금": "friday",
    "토": "saturday",
    "일": "sunday",
}

# 상태 판단 기준
SOON_THRESHOLD = 60  # 분 단위
DEFAULT_AVAILABLE_MINUTES = 9999


def lecture_to_dict(lec: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Mongo에서 가져온 강의 도큐먼트를 응답용 dict로 축약."""
    if lec is None:
        return None
    return {
        "course_name": lec.get("course_name"),
        "start_time": lec.get("start_time"),
        "end_time": lec.get("end_time"),
        "professor": lec.get("professor"),
    }


def extract_floor(room: str) -> str:
    """
    강의실 문자열에서 층 정보를 추출.
    예) '414' -> '4', 'B106' -> 'B1', '1201' -> '12'
    규칙:
      - 앞 1~2자리가 층(지하: 'B' + 숫자)
      - 숫자만 시작하면 마지막 두 자리는 호수로 보고 그 앞을 층으로 간주
    """
    # 지하(B) 포함 가능, 숫자 연속 캡처
    match = re.match(r"(B?\d+)", room)
    if not match:
        return "?"
    prefix = match.group(1)  # 예: 'B106' 또는 '414' 또는 '1201'

    if prefix.startswith("B"):
        # 'B106' -> 'B1' 로 처리
        # 'B' 다음의 첫 자리 숫자를 층으로 판단
        digits = prefix[1:]
        return f"B{digits[0]}" if digits else "B?"
    else:
        # '414' -> '4', '1201' -> '12'
        if len(prefix) <= 2:
            # '10' 같은 경우 전체가 층일 가능성: '10'층
            return prefix
        return prefix[:-2]


def determine_room_status(target_time: str,
                          next_lecture: Optional[Dict[str, Any]],
                          current_lecture: Optional[Dict[str, Any]]):
    """
    현재 수업/다음 수업 유무로 상태 문자열, 사용 가능 분, 메시지를 계산.
    """
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
    """
    건물/요일/시각(+선택: 층) 기준으로 강의실 상태를 조회.
    - 핵심 수정: 해당 요일에 수업이 '없어도' 건물(＋층)의 전체 방 목록을 기준으로 응답에 포함.
      → MongoDB distinct('room')로 모든 방 이름을 뽑은 뒤,
        그 중 요일에 해당하는 수업을 매핑하여 상태 계산.
    """
    db = get_database()
    target_time = f"{hour:02d}:{minute:02d}"

    # 요일 검증 및 변환
    day_eng = weekday_map.get(weekday)
    if not day_eng:
        return {"error": "잘못된 요일 형식입니다. (월~일 중 하나를 입력해주세요)"}

    # 1) 해당 요일의 수업 목록 조회
    lectures_query: Dict[str, Any] = {"building": int(building), "day": day_eng}
    if floor:
        # floor가 'B1', '4', '12' 형태라고 가정
        # 정규식 특수문자 이스케이프
        lectures_query["room"] = {"$regex": f"^{re.escape(floor)}"}

    cursor = db["2025_2_lectures"].find(lectures_query).sort("start_time", ASCENDING)
    lectures = await cursor.to_list(length=None)

    # 방 -> 그 요일의 강의 리스트 매핑
    rooms_dict: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for lec in lectures:
        rooms_dict[lec["room"]].append(lec)

    # 2) 건물(＋층)에 존재하는 모든 방 목록(요일 무관)
    rooms_filter: Dict[str, Any] = {"building": int(building)}
    if floor:
        rooms_filter["room"] = {"$regex": f"^{re.escape(floor)}"}

    all_rooms_set = set(await db["2025_2_lectures"].distinct("room", rooms_filter))
    # 안전망: 혹시 요일 쿼리로만 잡힌 방이 있으면 합집합
    all_rooms_set |= set(rooms_dict.keys())

    # 3) 정렬 키: 층 → 방이름
    def _sort_key(r: str):
        fl = extract_floor(r)  # 예: 'B1', '4', '12', '?'
        # 층을 정수/우선순위로 변환
        if fl.startswith("B"):
            # 지하층을 맨 앞쪽으로 (B1, B2, ...)
            try:
                bnum = int(fl[1:])  # 'B1' -> 1
            except ValueError:
                bnum = 99
            floor_key = -100 + (-bnum)  # B1 < B2 < ... < B99
        else:
            try:
                floor_key = int(fl)  # '12' -> 12
            except ValueError:
                floor_key = 999  # 알 수 없는 층은 맨 뒤
        return (floor_key, r)

    response: List[Dict[str, Any]] = []

    for room in sorted(all_rooms_set, key=_sort_key):
        room_lectures = rooms_dict.get(room, [])

        # 현재 / 다음 수업 판별
        current: Optional[Dict[str, Any]] = None
        next_lectures: List[Dict[str, Any]] = []

        for lec in room_lectures:
            if lec["start_time"] <= target_time < lec["end_time"]:
                current = lec
            elif lec["start_time"] > target_time:
                next_lectures.append(lec)

        next_lecture = next_lectures[0] if next_lectures else None
        status, available_minutes, soon_message = determine_room_status(
            target_time, next_lecture, current
        )

        response.append({
            "building": building,
            "floor": extract_floor(room),
            "room_number": room,
            "status": status,  # "empty" | "soon" | "in_use"
            "current_lecture": lecture_to_dict(current),
            "next_lecture": lecture_to_dict(next_lecture),
            "next_lectures": [lecture_to_dict(lec) for lec in next_lectures],
            "available_minutes": available_minutes,
            "soon_message": soon_message,
        })

    return response
