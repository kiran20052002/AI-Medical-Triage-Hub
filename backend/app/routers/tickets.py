from fastapi import APIRouter, Depends, Request, Form, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from app.dependencies import get_current_user, require_user
from app.models import Ticket, Patient, Doctor, ChatMessage
from beanie import PydanticObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


router = APIRouter(prefix="/tickets", tags=["Tickets"])



async def process_ticket_ai(ticket_id: str, title: str, description: str):
    from app.utils.ai_utils import analyze_ticket_ai

    ticket = await Ticket.get(ticket_id)
    if not ticket:
        return
    
    doctors = await Doctor.find_all().to_list()
    available_specialists = []
    for d in doctors:
        available_specialists.extend(d.specialist)
    available_specialists = list(set(available_specialists))


    analysis = await analyze_ticket_ai(title, description, available_specialists=available_specialists)

    if analysis:
        ticket.helpful_notes = analysis.get("helpfulNotes")
        ticket.priority = analysis.get("priority")
        ticket.specialist = analysis.get("specialist")
        
        required_specialists = analysis.get("specialist", [])
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    if user.role == "patient":
        tickets = await Ticket.find(Ticket.created_by == user.id).sort("-created_at").to_list()
        return {"tickets": tickets, "user": user}
    else:
        tickets = await Ticket.find(Ticket.assigned_to == user.id).sort("-created_at").to_list()
        patient_ids = [t.created_by for t in tickets]
        patients = await Patient.find({"_id": {"$in": patient_ids}}).to_list()
        patient_map = {str(p.id): p.email for p in patients}

        return {"tickets": tickets, "user": user, "patient_map": patient_map}




@router.post("/create")
async def create_ticket(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(...),
    user = Depends(require_user)
):
    from app.utils.ml_utils import verify_medical_query
    
    validation = await verify_medical_query(f"Title: {title}\nDescription: {description}")
    if validation and not validation.get("is_valid", True):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "invalid_ticket"})

    ticket = Ticket(
        title=title,
        description=description,
        created_by=user.id,
        status="TODO"
    )
    await ticket.insert()

    # Triger AI analysis in Background
    background_tasks.add_task(process_ticket_ai, str(ticket.id), title, description)
    return {"status": "success", "ticket_id": str(ticket.id)}


@router.get("/{id}")
async def get_ticket_detail(id: str, request: Request, user = Depends(require_user)):
    ticket = await Ticket.get(id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    assigned_email = None
    if ticket.assigned_to:
        doc = await Doctor.find_one(Doctor.id == ticket.assigned_to)
        if doc:
            assigned_email = doc.email
        else:
            assigned_email = "Unknown Doctor"
    else:
        assigned_email = "Unassigned"

    return {"ticket": ticket, "assigned_email": assigned_email, "user": user}


@router.post("/{id}/analyze-closure")
async def analyze_closure(id: str, background_tasks: BackgroundTasks, user = Depends(require_user)):

    from app.utils.ai_utils import generate_closure_summary, analyze_ticket_chat_ai

    ticket = await Ticket.get(id)
    if not ticket:
        return RedirectResponse("/tickets")
    
    # only doctor can close
    if user.role == "patient" and ticket.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    chat_history_text = ""
    if ticket.channel_id:
        try:
            # Fetch local messages
            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(50).to_list()
            
            formatted_messages = []
            for m in messages:
                formatted_messages.append({
                    "user": {"name": m.sender_name},
                    "text": m.text
                })
            
            analysis = await analyze_ticket_chat_ai(formatted_messages)
            if analysis and analysis.get("recommendedStatus") == "In Progress":
                reason = analysis.get("reasoning", "AI suggests further discussion.")
                print(f"Smart Close Blocked: {reason}")
                return {"status": "blocked", "message": f"Smart Close Blocked: {reason}"}

            chat_history_text = "\n".join([f"{m['user']['name']}: {m['text']}" for m in formatted_messages])
        
        except Exception as e:
            print(f"Warning: Failed to fetch chat history: {e}")
    
    context = (ticket.helpful_notes or "") + "\n\nChat History:\n" + chat_history_text
    summary = await generate_closure_summary(ticket.title, ticket.description, context)

    ticket.status = "completed"

    if ticket.helpful_notes:
        ticket.helpful_notes += f"\n\n[CLOSURE]: {summary}"
    else:
        ticket.helpful_notes = f"[CLOSURE]: {summary}"
    

    await ticket.save()

    return {"status": "closed", "message": "Ticket Closed Successfully. AI Summary added."}


@router.post("/{id}/request-connection")
async def request_connection(id: str, user = Depends(require_user)):
    ticket = await Ticket.get(id)
    if not ticket or ticket.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    if ticket.assigned_to and not ticket.connection_status:
        ticket.connection_status = "requested"
        await ticket.save()
    
    return RedirectResponse(f"/tickets/{id}", status_code=303)


@router.post("/{id}/accept-connection")
async def accept_connection(id: str, user = Depends(require_user)):
    ticket = await Ticket.get(id)
    if not ticket or ticket.assigned_to != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    if ticket.connection_status == "requested":
        # Connection Accepted - Set channel ID for Socket.io room identification
        try:
            ticket.channel_id = f"ticket-{ticket.id}"
            ticket.connection_status = "accepted"
            print(f"Room Created: {ticket.channel_id}")
            await ticket.save()

        except Exception as e:
            print(f"Error creating chat channel on acceptance: {e}")
    
    return RedirectResponse(f"/tickets/{id}", status_code=303)





    
    