from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.dependencies import get_current_user
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/tickets", tags=["Tickets"])
templates = Jinja2Templates(directory="app/templates")



@router.get("/")
async def get_tickets(request: Request, user = Depends(get_current_user)):
    if not user:
        return RedirectResponse("/auth/login")
    
    if user.role == "patient":
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
    else:
        return templates.TemplateResponse("dashboard_doctor.html", {"request": request, "user": user})



