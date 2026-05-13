from fastapi import APIRouter, Body, HTTPException, status
from app.utils.ai_utils import generate_embedding, generate_medical_response
from app.utils.ml_utils import verify_medical_query
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
    
    # 1. Generate Embedding
    try:
        embedding = await generate_embedding(query)
    except Exception as e:
        hurdles.append(f"Embedding Generation Failed: {str(e)}")
        embedding = None
    
    similarity_score = 0
    top_match = None

    if embedding:
        try:
            # 2. Search for similar reports
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": embedding,
                        "numCandidates": 10,
                        "limit": 1  # Get top 1 most relevant 
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
            results = await cursor.to_list(length=1)
            
            if results:
                top_match = results[0]
                similarity_score = top_match.get("score", 0)

        except Exception as e:
            print(f"Vector Search Error: {e}")
            hurdles.append(f"Vector Search Failed: {str(e)}")

    # 3. Decide response based on similarity score (Threshold 0.80)
    if top_match and similarity_score >= 0.8:

        assessment = top_match.get("content", {}).get("assessment", "N/A")
        plan = top_match.get("content", {}).get("plan", "N/A")
        ticket_id = top_match.get("ticketId", "Unknown") 
        
        context = f"""
          Diagnosis: {assessment}
          Plan/Treatment: {plan}
        """
        
        system_prompt = f"""You are a helpful and empathetic medical assistant chatbot.
      
      PRIMARY DIRECTIVE:
      You are strictly limited to medical and health-related topics.
      - If the user asks about general knowledge, coding, history, or anything NON-MEDICAL (e.g., "who is the father of computer?", "solve 2+2"), you MUST reply: "I am a medical assistant. I can only assist with health-related inquiries."
      - Do NOT try to answer non-medical questions, even if you know the answer.

      RAG INSTRUCTIONS:
      Your goal is to answer patient questions based ONLY on the provided Context (which comes from similar past resolved tickets).
      
      Rules:
      1. If the Context contains relevant medical advice or a solution, rephrase it in a friendly, helpful way for the patient.
      2. If the Context DOES NOT contain a relevant answer, strictly reply: "I'm sorry, I don't have enough information to answer that. Please create a support ticket so a doctor can assist you."
      3. Do not make up medical advice. Use only the provided context.
      4. EXCLUDE phrases that imply you are the doctor waiting for a follow-up (e.g., "report back to us", "we will check on you"). The user is chatting with an AI, not the original doctor.
      
      Context from similar past cases:
      {context}
      """
        
        try:
            bot_response = await generate_medical_response(system_prompt, query)
            
            refusal_prefix = "I am a medical assistant. I can only assist with health-related inquiries."
            
            if bot_response.strip().startswith(refusal_prefix):
                final_response = bot_response
            else:
                final_response = f"{bot_response}\n\n(Reference Ticket ID: {ticket_id})"

            return {
                "response": final_response, 
                "type": "answer",
                "hurdles": hurdles
            }
            
        except Exception as e:
            print(f"Chatbot AI Error: {e}")
            hurdles.append(f"Response Generation Failed: {str(e)}")
            # Fall through to default response

    # Fallback response (Low confidence, no match, or error occurred)
    return {
        "response": "I'm sorry, I cannot find a specific solution for that in our records. I recommend creating a ticket so a specialist can assist you.",
        "type": "suggestion",
        "hurdles": hurdles
    }