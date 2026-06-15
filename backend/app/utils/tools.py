from typing import List, Optional
from langchain_core.tools import tool
from app.utils.ai_utils import generate_embedding
from app.models import Report

@tool
async def search_medical_records(query: str) -> str:
    """
    Searches the medical records database for past cases and reports similar to the user's query.
    Returns a string containing the most relevant medical assessment and treatment plan.
    """
    try:
        # 1. Generate Embedding
        embedding = await generate_embedding(query)
        
        # 2. Vector Search Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": 10,
                    "limit": 3  # Retrieve top 3 for better context
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "ticketId": 1, 
                    "content.plan": 1,
                    "content.assessment": 1,
                    "score": { "$meta": "vectorSearchScore" }
                }
            }
        ]
        
        collection = Report.get_pymongo_collection()
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=3)
        
        if not results:
            return "No matching medical records found for this query."
        
        # 3. Format results
        formatted_results = []
        for res in results:
            score = res.get("score", 0)
            # Only include if score is decent (e.g., > 0.6)
            if score >= 0.6:
                ticket_id = res.get("ticketId", "Unknown")
                assessment = res.get("content", {}).get("assessment", "N/A")
                plan = res.get("content", {}).get("plan", "N/A")
                formatted_results.append(
                    f"--- Record (Ticket ID: {ticket_id}, Match Score: {score:.2f}) ---\n"
                    f"Assessment: {assessment}\n"
                    f"Plan: {plan}\n"
                )
        
        if not formatted_results:
            return "No highly relevant medical records found."
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error during medical record retrieval: {str(e)}"