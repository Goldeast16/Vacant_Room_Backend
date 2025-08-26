from fastapi import FastAPI
from routes.rooms import router as rooms_router
from routes.health import health_router
from routes.timetable import router as timetable_router
from routes.feedback import router as feedback_router
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 MongoDB 연결
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    app.mongodb_client = mongo_client
    app.database = mongo_client.get_default_database()

    try:
        await app.database.command("ping")
        print("MongoDB 연결 성공")

        # 인덱스 생성
        await app.database["2025_2_lectures"].create_index(
            [("building", 1), ("room", 1), ("day", 1), ("start_time", 1)]
        )
        print("timetable 인덱스 확인/생성 완료")

    except Exception as e:
        print("MongoDB 연결 실패:", e)
        raise e

    yield

    # 앱 종료 시 연결 해제
    mongo_client.close()
    print("MongoDB 연결 종료")

app = FastAPI(lifespan=lifespan)

app.include_router(rooms_router, prefix="/api")
app.include_router(health_router)
app.include_router(timetable_router)
app.include_router(feedback_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)