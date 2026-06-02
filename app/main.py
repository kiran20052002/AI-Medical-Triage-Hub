from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.config.db import init_db
from app.utils.agent import create_agent_graph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from dotenv import load_dotenv



load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Initialize LangGraph Checkpointer and Agent
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app.state.saver = saver
        app.state.agent = create_agent_graph(checkpointer=saver)
        yield
    
    # Shutdown

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

from app.routers import auth, tickets, chat, chatbot, reports, admin


app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(chat.router)
app.include_router(chatbot.router)
app.include_router(reports.router)
app.include_router(admin.router)

@app.get("/")
async def home(request: Request):
    return RedirectResponse("/auth/login") 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
