import asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.models import Report, Ticket, Patient, Doctor
import os
from dotenv import load_dotenv

async def check_db():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("MONGO_URI not found")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    await init_beanie(database=client.get_default_database(), document_models=[Report, Ticket, Patient, Doctor])
    
    reports_count = await Report.find_all().count()
    tickets_count = await Ticket.find_all().count()
    
    print(f"Reports: {reports_count}")
    print(f"Tickets: {tickets_count}")
    
    if reports_count > 0:
        latest_report = await Report.find_all().sort("-created_at").first_or_none()
        print(f"Latest Report ID: {latest_report.id}")
        print(f"Latest Report Embedding Len: {len(latest_report.embedding)}")
        print(f"Latest Report Content: {latest_report.content}")
        print(f"Latest Report Formatted: {latest_report.formatted_report}")
    
    if tickets_count > 0:
        latest_ticket = await Ticket.find_all().sort("-created_at").first_or_none()
        print(f"Latest Ticket Status: {latest_ticket.status}")

if __name__ == "__main__":
    asyncio.run(check_db())
