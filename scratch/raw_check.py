import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

async def raw_check():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.get_default_database()
    
    print(f"Database: {db.name}")
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")
    
    count = await db.reports.count_documents({})
    print(f"Reports Count: {count}")
    
    doc = await db.reports.find_one({})
    if doc:
        print(f"Sample Report Keys: {doc.keys()}")
        if 'embedding' in doc:
             print(f"Embedding length: {len(doc['embedding'])}")
        else:
             print("NO EMBEDDING FIELD")

if __name__ == "__main__":
    asyncio.run(raw_check())
