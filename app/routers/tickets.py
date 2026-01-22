from fastapi import APIRouter, Request, Depends, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from app.dependencies import get_current_user, require_user
from fastapi.responses import RedirectResponse
from app.models import Ticket, Doctor, Patient

router = APIRouter(prefix="/tickets", tags=["Tickets"])
templates = Jinja2Templates(directory="app/templates")



async def process_ticket_ai(ticket_id: str, title: str, description: str):
    from app.utils.auth_utils import analyze_ticket_ai

    ticket = await Ticket.get(ticket_id)
    if not ticket:
        return
    
    analysis = await analyze_ticket_ai(title, description)
    if analysis:
        ticket.helpful_notes = analysis.get("helpfulNotes")
        ticket.priority = analysis.get("priority")
        ticket.specialist = analysis.get("specialist")
        if analysis.get("summary"):
            pass

        required_specialists = analysis.get("specialist",[])
        if required_specialists:

            doctor = await Doctor.find_one({"specialist": {"$in": required_specialists}})

            if doctor:
                ticket.assigned_to = doctor.id
                ticket.status = "In Progress"

                print(f"Auto-Assigned Ticket to Dr. {doctor.email}")
            else:
                print(f"No matching specialist found for: {required_specialists}")  

        await ticket.save()


@router.get("/")
async def get_tickets(request: Request, user = Depends(require_user)):
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

    # Triger AI analysis in Background
    background_tasks.add_task(process_ticket_ai, str(ticket.id), title, description)
    return RedirectResponse("/tickets", status_code=303)
    


