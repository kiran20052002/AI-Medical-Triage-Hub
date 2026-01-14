from fastapi import FastAPI,Request
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.config.db import init_db
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

from app.routers import auth

app.include_router(auth.router)

@app.get('/')
async def home(request: Request):
    return RedirectResponse("/auth/login")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
