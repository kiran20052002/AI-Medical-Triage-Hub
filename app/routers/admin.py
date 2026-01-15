from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class = HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("dashboard_admin.html",{"request": request})