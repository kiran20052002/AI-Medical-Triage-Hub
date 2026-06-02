from fastapi import APIRouter, Depends, Request
from stream_chat import StreamChat
import os
from app.dependencies import require_user, get_current_user
from dotenv import load_dotenv

load_dotenv()


router = APIRouter(prefix="/chat", tags=["Chat"])

api_key = os.getenv("STREAM_API_KEY")
api_secret = os.getenv("STREAM_API_SECRET")

# Initialize Server Client
server_client = StreamChat(api_key, api_secret)




@router.get("/token")
async def get_token(user = Depends(require_user)):
    user_id = str(user.id)
    token = server_client.create_token(user_id)

    # sync user to stream
    server_client.upsert_user({
        "id": user_id,
        "name": user.email,
        "role": "user"
    })

    return {
        "token": token, 
        "stream_api_key": api_key, 
        "userId": user_id,
        "user_id": user_id, 
        "user_name": user.email
    }
    