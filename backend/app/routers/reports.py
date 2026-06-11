from fastapi import APIRouter, Depends, Form, BackgroundTasks, HTTPException, status
from app.dependencies import require_user
from app.models import Ticket, Report, ChatMessage
from beanie import PydanticObjectId
import os
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/reports", tags=["Reports"])


async def process_report_embedding(report_id: str, text_content: str):
    embedding = await generate_embedding(text_content)
    if embedding:
        report = await Report.get(report_id)
        if report:
            report.embedding = embedding
            await report.save()
            print(f"Report {report_id} Embedded")


@router.post("/generate")
async def generate_report(
    background_tasks: BackgroundTasks,
    ticket_id: str = Form(...),
    user = Depends(require_user)
):

    ticket = await Ticket.get(ticket_id)
    if not ticket or ticket.status != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticket or status")
    
    # 1. Fetch Chat History
    chat_transcript = ""
    if ticket.channel_id:
        try:
            # Fetch local messages
            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(100).to_list()
            chat_transcript = "\n".join([f"{m.sender_name}: {m.text}" for m in messages])
        
        except Exception as e:
            print(f"Failed to fetch chat for report: {e}")
    
    # 2. Generate Triage Report
    triage_content = await generate_soap_note(ticket.title, ticket.description, chat_transcript)

    if not triage_content:
        triage_content = {
            "subjective": f"Complaint: {ticket.title}\n{ticket.description}",
            "objective": "None reported",
            "assessment": "Pending AI analysis",
            "plan": "Follow up required"
        }
    

    # 3. Format Report (Clinical Triage Summary)
    formatted_report = f"""
    **SUBJECTIVE**: {triage_content.get('subjective', '')}
    **OBJECTIVE**: {triage_content.get('objective', '')}
    **ASSESSMENT**: {triage_content.get('assessment', '')}
    **PLAN**: {triage_content.get('plan', '')}
    """.strip()

    # 4. Save Report
    report = Report(
        content=triage_content,
        formatted_report=formatted_report,
        ticket_id=str(ticket.id)
    )

    triage_content['ticket_id'] = str(ticket.id)
    triage_content['doctor_id'] = str(user.id)

    report.content = triage_content
    await report.insert()

    # 5. Update Ticket Status
    ticket.status = "Report Sent"
    await ticket.save()

    # 6. Trigger Embedding
    text_to_embed = f"Subjective: {triage_content.get('subjective')}\nObjective: {triage_content.get('objective')}\nAssessment: {triage_content.get('assessment')}"
    background_tasks.add_task(process_report_embedding, str(report.id), text_to_embed)

    return RedirectResponse("/tickets", status_code=303)

    