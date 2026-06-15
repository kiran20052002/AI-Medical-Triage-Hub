from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.db import init_db
from app.utils.agent import create_agent_graph
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
import os
import json
from dotenv import load_dotenv
from app.models import ChatMessage, Patient, Doctor
from beanie import PydanticObjectId
from typing import List, Dict, Set

load_dotenv()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # room_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()
        self.active_connections[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Initialize checkpointer and agent
    sync_client = MongoClient(os.getenv("MONGO_URI"))
    saver = MongoDBSaver(sync_client, db_name="langgraph_state")
    
    app.state.saver = saver
    app.state.agent = create_agent_graph(checkpointer=saver)
    
    yield
    
    # Shutdown
    sync_client.close()
    

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/{ticket_id}")
async def websocket_endpoint(websocket: WebSocket, ticket_id: str):
    room_id = f"ticket-{ticket_id}"
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            t_id = message_data.get("ticketId")
            sender_id = message_data.get("senderId")
            sender_name = message_data.get("senderName") or "Unknown User"
            sender_role = message_data.get("senderRole") or "user"
            text = message_data.get("text")
            
            if t_id and text and sender_id:
                message = ChatMessage(
                    ticket_id=PydanticObjectId(t_id),
                    sender_id=PydanticObjectId(sender_id),
                    sender_name=sender_name,
                    sender_role=sender_role,
                    text=text
                )
                await message.insert()

                broadcast_data = {
                    "ticketId": str(t_id),
                    "senderId": str(sender_id),
                    "senderName": sender_name,
                    "senderRole": sender_role,
                    "text": text,
                    "createdAt": message.created_at.isoformat()
                }
                await manager.broadcast(broadcast_data, room_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, room_id)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth, tickets, chat, chatbot, reports, admin


app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(chat.router)
app.include_router(chatbot.router)
app.include_router(reports.router)
app.include_router(admin.router)

@app.get("/")
async def home(request: Request):
    return {"message": "Welcome to the Medical Triage Hub API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
