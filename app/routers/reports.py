from fastapi import APIRouter, Depends, Form, BackgroundTasks
from fastapi.responses import RedirectResponse
from app.dependencies import require_user
from app.models import Ticket, Report
from app.utils.ai_utils import generate_embedding


router = APIRouter(prefix="/reports", tags=["Reports"])


async def process_report_embedding(report_id: str, text_content: str):
    embedding = await generate_embedding(text_content)
    if embedding:
        report = Report.get(report_id)
        if report:
            report.embedding = embedding
            await(report.save())
            print(f"Report {report_id} Embedded")


@router.post("/generate")
async def generate_report(
    background_taks: BackgroundTasks,
    ticket_id: str = Form(...),
    user = Depends(require_user)
):
    from app.utils.ai_utils import generate_triage_report
    from stream_chat import StreamChat
    import os

    # Retrieve ticket
    ticket = Ticket.get(ticket_id)
    if not ticket or ticket.status != "completed":
        return RedirectResponse("/tickets", status_code=303)
    
    # 1. Fetch Chat History
    chat_transcript = ""
    if ticket.channel_id:
        try:
            api_key = os.getenv("STREAM_API_KEY")
            api_secret = os.getenv("STREAM_API_SECRET")
            server_client = StreamChat(api_key=api_key, api_secret=api_secret)

            channel = server_client.channel("messaging", ticket.channel_id)

            # Fetch last 100 messages
            messages = channel.query(messages={'limit': 100})['messages']
            chat_transcript = "\n".join([f"{m.get('user', {}).get('name', 'User')}: {m.get('text', '')}" for m in messages])
        
        except Exception as e:
            print(f"Failed to fetch chat for report: {e}")
    
    # 2. Generate Triage Report
    triage_content = await generate_triage_report(ticket.title, ticket.description, chat_transcript)

    if not triage_content:
        triage_content = {
            "chief_complaint": f"Complaint: {ticket.title}\n{ticket.description}",
            "symptoms_observations": "None reported",
            "triage_assessment": "Pending AI analysis",
            "recommended_plan": "Follow up required"
        }
    

    # 3. Format Report (Clinical Triage Summary)
    formatted_report = f"""
    **CHIEF COMPLAINT**: {triage_content.get('chief_complaint', '')}
    **SYMPTOMS & OBSERVATIONS**: {triage_content.get('symptoms_observations', '')}
    **ASSESSMENT**: {triage_content.get('triage_assessment', '')}
    **PLAN**: {triage_content.get('recommended_plan', '')}
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
    text_to_embed = f"Chief Complaint: {triage_content.get('chief_complaint')}\nSymptoms: {triage_content.get('symptoms_observations')}\nAssessment: {triage_content.get('triage_assessment')}"
    background_taks.add_task(process_report_embedding, str(report.id), text_to_embed)

    return RedirectResponse("/tickets", status_code=303)

    
