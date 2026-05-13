import asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.models import Report, Ticket, Patient, Doctor
from app.utils.ai_utils import generate_embedding
import os
from dotenv import load_dotenv

async def test_vector_search():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")
    client = AsyncIOMotorClient(mongo_uri)
    await init_beanie(database=client.get_default_database(), document_models=[Report, Ticket, Patient, Doctor])
    
    query = "I have been feeling very sick with fever"
    print(f"Generating embedding for: {query}")
    embedding = await generate_embedding(query)
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": embedding,
                "numCandidates": 10,
                "limit": 1
            }
        },
        {
            "$project": {
                "_id": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]
    
    print("Running aggregation...")
    try:
        collection = Report.get_pymongo_collection()
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=1)
        print(f"Results: {results}")
    except Exception as e:
        print(f"Aggregation Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_vector_search())
