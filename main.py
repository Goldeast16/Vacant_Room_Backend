from fastapi import FastAPI, Request
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

CONNECTION_STRING = os.getenv("MONGODB_URI")

@asynccontextmanager
async def db_lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(CONNECTION_STRING)
    app.database = app.mongodb_client.get_default_database()

    try:
        ping_response = await app.database.command("ping")
        if int(ping_response["ok"]) != 1:
            raise Exception("MongoDB ping failed")
        print("✅ MongoDB 연결 성공")
    except Exception as e:
        print("❌ MongoDB 연결 실패:", e)
        raise e

    yield

    app.mongodb_client.close()
    print("🛑 MongoDB 연결 종료")

app = FastAPI(lifespan=db_lifespan)

# Test API Code
def convert_objectid(doc):
    doc["_id"] = str(doc["_id"])
    return doc

from fastapi import Query
from datetime import datetime

@app.get("/lectures/search")
async def search_lectures(
    request: Request,
    building: int = Query(...),
    floor: str = Query(...),  # 예: "4"
    start_time: str = Query(...),  # "14:00"
    end_time: str = Query(...)     # "18:00"
):
    db = request.app.database
    collection = db["2025_2_lectures"]

    # 해당 층의 room들만 필터링 (예: "414" → floor "4" 포함)
    floor_prefix = floor + ""

    # 시간 비교를 위해 string을 datetime.time으로 파싱
    def to_time(time_str):
        return datetime.strptime(time_str, "%H:%M").time()

    start = to_time(start_time)
    end = to_time(end_time)

    results = []
    async for doc in collection.find({"building": building}):
        room_floor = str(doc.get("room", ""))[:len(floor_prefix)]
        doc_start = to_time(doc.get("start_time"))
        doc_end = to_time(doc.get("end_time"))

        # 같은 층이고 시간대가 겹치는 강의만 필터링
        if (
            room_floor == floor_prefix and
            not (doc_end <= start or doc_start >= end)
        ):
            results.append(convert_objectid(doc))

    return {"count": len(results), "results": results}

# 각 강의실별로 시간표 데이터를 만들어두면 좀 더 제공하기 편하려나?