from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.config.db import init_db
from app.utils.agent import create_agent_graph
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
import os
from dotenv import load_dotenv



load_dotenv()

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
