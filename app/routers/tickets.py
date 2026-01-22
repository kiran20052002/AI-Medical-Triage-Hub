from fastapi import APIRouter, Request, Depends, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from app.dependencies import get_current_user
from fastapi.responses import RedirectResponse
from app.models import Ticket

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



@router.post("/create")
async def create_ticket(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    user = Depends(require_user)
):
    ticket = Ticket(
        title=title,
        description=description,
        created_by=user.id,
        status="TODO"
    )
    await ticket.insert()

    
    return RedirectResponse("/tickets", status_code=303)
    


