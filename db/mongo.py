from motor.motor_asyncio import AsyncIOMotorClient
import os

def get_database():
    mongo_uri = os.getenv("MONGODB_URI")
    client = AsyncIOMotorClient(mongo_uri)
    return client.get_default_database()
