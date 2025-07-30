from fastapi import FastAPI
from routes.rooms import router as rooms_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.include_router(rooms_router, prefix="/api")

# protected?