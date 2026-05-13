from fastapi import APIRouter, Body, HTTPException, status
from app.utils.ai_utils import generate_embedding, generate_medical_response
from app.utils.ml_utils import verify_medical_query
from app.utils.agent import agent_executor
from app.models import Report

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

@router.post("/query")
async def chat_query(payload: dict = Body(...)):
    query = payload.get("query")
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query is required"
        )
    
    # Initialize hurdles list to capture errors
    hurdles = []
    
    # 0. Validate Query Type (Gibberish / Non-Medical)
    validation = await verify_medical_query(query)
    if validation and not validation.get("is_valid"):
        return {
            "response": "I'm sorry, that doesn't look like a valid health inquiry. I can only assist with medical topics. Please provide a clear description of your symptoms.",
            "type": "suggestion",
            "hurdles": hurdles
        }
    
    # 1. Execute Agentic RAG Graph
    try:
        # Initial state for the agent
        initial_state = {
            "query": query,
            "documents": "",
            "retry_count": 0,
            "response": "",
            "mode": ""
        }
        
        # Run the agentic workflow
        result = await agent_executor.ainvoke(initial_state)
        
        final_response = result.get("response", "I'm sorry, I encountered an issue processing your request.")
        
        # Determine the response type for the frontend
        resp_type = "answer" if "Ticket ID" in final_response or "Assessment" in final_response else "suggestion"
        if "⚠️ EMERGENCY" in final_response:
            resp_type = "emergency"

        return {
            "response": final_response, 
            "type": resp_type,
            "hurdles": hurdles
        }
        
    except Exception as e:
        print(f"Agentic Chatbot Error: {e}")
        hurdles.append(f"Agent Execution Failed: {str(e)}")
        return {
            "response": "I'm sorry, I am having trouble connecting to my medical knowledge base right now. Please try again later or create a support ticket.",
            "type": "suggestion",
            "hurdles": hurdles
        }