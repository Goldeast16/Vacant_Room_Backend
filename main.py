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

@app.get("/movies")
async def get_movies(request: Request):
    db = request.app.database
    cursor = db["movies"].find().limit(10)  # 10개만 가져오기
    movies = []
    async for doc in cursor:
        movies.append(convert_objectid(doc))
    return {"count": len(movies), "movies": movies}

#backup