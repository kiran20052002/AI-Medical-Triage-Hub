from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import require_user
from app.models import ChatMessage
from beanie import PydanticObjectId

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/history/{ticket_id}")
async def get_chat_history(ticket_id: str, user = Depends(require_user)):
    try:
        messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket_id)).sort("created_at").to_list()
        return {"messages": messages}
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat history")

# Deprecated/Removed Stream Token logic
@router.get("/token")
async def get_token_stub(user = Depends(require_user)):
    return {
        "status": "deprecated",
        "userId": str(user.id),
        "user_id": str(user.id),
        "user_name": user.email
    }
    