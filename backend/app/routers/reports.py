from fastapi import APIRouter, Depends, Form, HTTPException, status
from app.dependencies import require_user
from app.models import Ticket, Report, ChatMessage
from beanie import PydanticObjectId
import os
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate")
async def generate_report(
    ticket_id: str = Form(...),
    user = Depends(require_user)
):

    ticket = await Ticket.get(ticket_id)
    if not ticket or ticket.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket or status")
    
    chat_transcript = ""
    if ticket.channel_id:
        try:

            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(100).to_list()
            chat_transcript = "\n".join([f"{m.sender_name}: {m.text}" for m in messages])
        
        except Exception as e:
            print(f"Failed to fetch chat for report: {e}")
    

    triage_content = await generate_soap_note(ticket.title, ticket.description, chat_transcript)

    if not triage_content:
        triage_content = {
            "subjective": f"Complaint: {ticket.title}\n{ticket.description}",
            "objective": "None reported",
            "assessment": "Pending AI analysis",
            "plan": "Follow up required"
        }
    


    formatted_report = f"""
    **SUBJECTIVE**: {triage_content.get('subjective', '')}
    **OBJECTIVE**: {triage_content.get('objective', '')}
    **ASSESSMENT**: {triage_content.get('assessment', '')}
    **PLAN**: {triage_content.get('plan', '')}
    """.strip()


    report = Report(
        content=triage_content,
        formatted_report=formatted_report,
        ticket_id=str(ticket.id)
    )

    triage_content['ticket_id'] = str(ticket.id)
    triage_content['doctor_id'] = str(user.id)

    report.content = triage_content
    await report.insert()

    ticket.status = "Report Sent"
    await ticket.save()

    return RedirectResponse("/tickets", status_code=303)

    