from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from pymongo import MongoClient
import re  # 정규 표현식 추가

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # 프론트엔드 URL에 맞게 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB 연결
client = MongoClient("mongodb://localhost:27017")
db = client["lecture_db"]
rooms_collection = db["rooms3"]

# 강의 정보 모델
class Lecture(BaseModel):
    course: str
    start: str
    end: str

# 강의실 출력 모델
class RoomOut(BaseModel):
    building: str
    floor: str  # floor를 문자열로 처리
    room_number: str
    status: str
    current_lecture: Optional[Lecture] = None
    next_lecture: Optional[Lecture] = None
    soon_message: Optional[str] = None
    available_minutes: Optional[int] = None

# 시간표 출력 모델
class TimetableOut(BaseModel):
    course: str
    start: str
    end: str

# 기본 경로
@app.get("/")
async def root():
    return {"message": "Welcome to the Lecture Room API"}

# 건물 목록 가져오기
@app.get("/api/buildings", response_model=List[str])
async def get_buildings():
    buildings = rooms_collection.distinct("building")
    return buildings

# 강의실 목록 가져오기
@app.get("/api/rooms", response_model=List[RoomOut])
async def get_rooms(building: str, hour: int, minute: int, weekday: str, floor: Optional[str] = None):
    current_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    filtered_rooms = []

    # 기본 쿼리: 건물만 기준으로
    query = {"building": building}
    
    # floor가 "all"이 아닌 경우에만 쿼리 필터에 추가
    if floor and floor != "all":  # floor가 "all"이 아닐 경우만 필터를 적용
        query["floor"] = floor  # floor는 문자열 그대로 저장되므로 변환 필요 없음
    
    rooms_cursor = rooms_collection.find(query)

    for room in rooms_cursor:
        lectures = room.get("lectures_by_day", {}).get(weekday, [])
        status = "empty"
        current_lecture = None
        next_lecture = None
        soon_message = None
        available_minutes = 1440  # 기본 값 (하루의 분)

        for lec in lectures:
            start_time = datetime.strptime(lec["start"], "%H:%M").replace(
                year=current_time.year, month=current_time.month, day=current_time.day)
            end_time = datetime.strptime(lec["end"], "%H:%M").replace(
                year=current_time.year, month=current_time.month, day=current_time.day)

            if start_time <= current_time < end_time:
                status = "in_use"
                current_lecture = Lecture(**lec)
                available_minutes = 0
                break
            elif current_time < start_time <= current_time + timedelta(hours=1):
                if status != "in_use":
                    status = "soon"
                    soon_message = f"{(start_time - current_time).seconds // 60}분 뒤 {lec['course']} 수업이 시작됩니다."
                    available_minutes = (start_time - current_time).seconds // 60
                    next_lecture = Lecture(**lec)
            elif current_time < start_time and (next_lecture is None or start_time < datetime.strptime(next_lecture.start, "%H:%M")):
                next_lecture = Lecture(**lec)

        filtered_rooms.append({
            "building": room["building"],
            "floor": room["floor"],  # 그대로 사용
            "room_number": room["room_number"],
            "status": status,
            "current_lecture": current_lecture,
            "next_lecture": next_lecture,
            "soon_message": soon_message,
            "available_minutes": available_minutes
        })

    filtered_rooms.sort(key=lambda x: x["available_minutes"], reverse=True)
    return filtered_rooms

# 특정 강의실 시간표 가져오기
@app.get("/api/room-timetable", response_model=List[TimetableOut])
async def get_room_timetable(building: str, room_number: str, weekday: str):
    room = rooms_collection.find_one({"building": building, "room_number": room_number})
    if room:
        lectures = room.get("lectures_by_day", {}).get(weekday, [])
        return [TimetableOut(**lec) for lec in lectures]
    return []

# 건물에 해당하는 층 목록 가져오기
@app.get("/api/floors", response_model=List[str])
async def get_floors(building: str):
    floors = set()
    rooms_cursor = rooms_collection.find({"building": building})
    for room in rooms_cursor:
        floors.add(room["floor"])  # floor는 문자열로 저장되어 있으므로 바로 추가
    return sorted(floors)
