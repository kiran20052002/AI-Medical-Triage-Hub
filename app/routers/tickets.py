from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from app.dependencies import get_current_user, require_user
from app.models import Ticket, Patient, Doctor
from datetime import datetime
import os
from stream_chat import StreamChat
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("STREAM_API_KEY")
api_secret = os.getenv("STREAM_API_SECRET")
server_client = StreamChat(api_key=api_key, api_secret=api_secret)


router = APIRouter(prefix="/tickets", tags=["Tickets"])
templates = Jinja2Templates(directory="app/templates")



async def process_ticket_ai(ticket_id: str, title: str, description: str):
    from app.utils.auth_utils import analyze_ticket_ai

    ticket = await Ticket.get(ticket_id)
    if not ticket:
        return
    
    # Analyze Ticket using AI
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


                # Create Chat Channel
                try:
                    from stream_chat import StreamChat
                    import os

                    api_key = os.getenv("STREAM_API_KEY")
                    api_secret = os.getenv("STREAM_API_SECRET")
                    task_client = StreamChat(api_key=api_key, api_secret=api_secret)

                    patient = await Patient.get(ticket.created_by)

                    patient_id = str(ticket.created_by)
                    doctor_id = str(doctor.id)

                    patient_name = patient.email if patient else "Unknown Patient"
                    doctor_name = doctor.email if doctor else "Unknown Doctor"

                    task_client.upsert_user(
                        {
                            "id": patient_id,
                            "role": "user",
                            "name": patient_name
                        }
                    )
                    task_client.upsert_user({
                        "id": doctor_id,
                        "role": "user",
                        "name": doctor_name
                    })

                    channel_id = f"ticket-{ticket.id}"
                    channel = task_client.channel(
                        "messaging",
                        channel_id,
                        {
                            "created_by_id": patient_id,
                            "members": [patient_id, doctor_id],
                            "name": f"Ticket: {ticket.title}"
                        }
                    )

                    channel.create(patient_id)
                    ticket.channel_id = channel_id
                    print(f"Chat Channel Created: {channel_id}")

                except Exception as e:
                    print(f"Error creating chat channel: {e}")


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
    


