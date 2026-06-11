from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
from app.models import Patient, Doctor, Ticket, Report, RefreshToken, ChatMessage

async def init_db():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db_name = client.get_default_database().name
    print(f"Connecting to Database: {db_name}")
    await init_beanie(database=client.get_default_database(), document_models=[Patient, Doctor, Ticket, Report, RefreshToken, ChatMessage])
    