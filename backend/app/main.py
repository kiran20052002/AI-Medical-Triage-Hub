from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.db import init_db
from app.utils.agent import create_agent_graph
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import socketio
from app.models import ChatMessage, Patient, Doctor
from beanie import PydanticObjectId

load_dotenv()

# Initialize Socket.io
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

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

# Mount Socket.io
app.mount("/socket.io", socket_app)

@sio.event
async def connect(sid, environ):
    print(f"Socket connected: {sid}")

@sio.event
async def join_room(sid, data):
    room = data.get("room")
    if room:
        await sio.enter_room(sid, room)
        print(f"User {sid} joined room: {room}")

@sio.event
async def send_message(sid, data):
    ticket_id = data.get("ticketId")
    sender_id = data.get("senderId")
    sender_name = data.get("senderName")
    sender_role = data.get("senderRole")
    text = data.get("text")
    
    if ticket_id and text:
        # Save to database
        message = ChatMessage(
            ticket_id=PydanticObjectId(ticket_id),
            sender_id=PydanticObjectId(sender_id),
            sender_name=sender_name,
            sender_role=sender_role,
            text=text
        )
        await message.insert()
        
        # Broadcast to room
        await sio.emit("new_message", {
            "ticketId": str(ticket_id),
            "senderId": str(sender_id),
            "senderName": sender_name,
            "senderRole": sender_role,
            "text": text,
            "createdAt": message.created_at.isoformat()
        }, room=f"ticket-{ticket_id}")

@sio.event
async def disconnect(sid):
    print(f"Socket disconnected: {sid}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
