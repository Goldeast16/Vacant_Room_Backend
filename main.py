from fastapi import FastAPI
from routes.rooms import router as rooms_router
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()
app.include_router(rooms_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Vue dev server 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

