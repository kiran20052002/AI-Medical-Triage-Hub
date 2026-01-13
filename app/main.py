from fastapi import FastAPI,Request
from fastapi.responses import RedirectResponse

app = FastAPI()

from app.routers import auth

app.include_router(auth.router)

@app.get('/')
async def home(request: Request):
    return RedirectResponse("/auth/login")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
