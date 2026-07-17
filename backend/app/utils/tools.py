from typing import List, Optional
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from app.utils.ai_utils import generate_embedding, llm, analyze_ticket_chat_ai, generate_closure_summary, generate_soap_note, pinecone_index
from app.models import Report, Ticket, Patient, ChatMessage, MedicalDocumentChunk, MedicalDocumentParent
from beanie import PydanticObjectId
from langgraph.types import interrupt
import asyncio
import httpx
from langchain_core.runnables import RunnableConfig

@tool
async def search_medical_knowledge(query: str) -> str:
    """
    Searches the verified medical knowledge base for information to answer the user's query.
    Returns excerpts from medical documents (e.g. guidelines, PDFs) relevant to the query.
    """
    try:
        embedding = await generate_embedding(query)

        if not pinecone_index:
            return "Vector database is not configured."
            
        query_response = pinecone_index.query(
            vector=embedding,
            top_k=3,
            include_metadata=True
        )
        
        results = query_response.get("matches", [])
        
        if not results:
            return "No matching medical knowledge found for this query."
        
        
        formatted_results = []
        parent_ids_fetched = set()
        for res in results:
            score = res.get("score", 0)
            if score >= 0.6:
                metadata = res.get("metadata", {})
                parent_id = metadata.get("parentId")
                if parent_id and str(parent_id) not in parent_ids_fetched:
                    parent_doc = await MedicalDocumentParent.get(PydanticObjectId(parent_id))
                    if parent_doc:
                        formatted_results.append(
                            f"--- Source: {parent_doc.title} ---\n{parent_doc.content}\n"
                        )
                        parent_ids_fetched.add(str(parent_id))
        
        if not formatted_results:
            return "No highly relevant medical knowledge found."
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error during medical knowledge retrieval: {str(e)}"

@tool
async def create_ticket(title: str, description: str, config: RunnableConfig) -> str:
    """
    Creates a support ticket for the patient. Use this tool if the user explicitly asks to create a support ticket, raise a complaint, or open a case for a specialist.
    """

    approval = interrupt({
        "action": "approve_ticket",
        "title": title,
        "description": description
    })
    

    if not approval or not approval.get("approved", False):
        return "Ticket creation cancelled by user."
        

    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        fallback_patient = await Patient.find_one()
        if fallback_patient:
            user_id = str(fallback_patient.id)
        else:
            return "Error: You must be logged in to create a ticket."
            
    ticket = Ticket(
        title=title,
        description=description,
        created_by=PydanticObjectId(user_id),
        status="TODO"
    )
    await ticket.insert()
    
    from app.routers.tickets import process_ticket_ai
    asyncio.create_task(process_ticket_ai(str(ticket.id), title, description))
    
    return f"Ticket successfully created! Ticket ID: {ticket.id}."

@tool
async def list_tickets(config: RunnableConfig) -> str:
    """
    Lists the tickets created by the user. Use this tool if the user asks to see their tickets, list their open cases, or check status.
    """
    try:
        user_id = config.get("configurable", {}).get("user_id")
        user_role = config.get("configurable", {}).get("user_role")
        
        if not user_id:
            fallback_patient = await Patient.find_one()
            if fallback_patient:
                user_id = str(fallback_patient.id)
                user_role = "patient"
            else:
                return "Error: You must be logged in to list tickets."
                
        if user_role == "doctor":
            tickets = await Ticket.find(Ticket.assigned_to == PydanticObjectId(user_id)).sort("-created_at").to_list()
            if not tickets:
                return "You have no tickets currently assigned to you."
            formatted = [
                "CRITICAL INSTRUCTION: You MUST show the following list to the user verbatim in your response. Do not summarize it. Preserve all markdown formatting.",
                "Here are the tickets currently assigned to you:"
            ]
            for t in tickets:
                formatted.append(f"- Ticket ID: {t.id} | Title: {t.title} | Status: {t.status} | Priority: {t.priority or 'N/A'}")
            return "\n".join(formatted)
        else:
            tickets = await Ticket.find(Ticket.created_by == PydanticObjectId(user_id)).sort("-created_at").to_list()
            if not tickets:
                return "You have not submitted any support tickets yet."
            formatted = [
                "CRITICAL INSTRUCTION: You MUST show the following list to the user verbatim in your response. Do not summarize it. Preserve all markdown formatting.",
                "Here are your submitted tickets:"
            ]
            for t in tickets:
                formatted.append(f"- Ticket ID: {t.id} | Title: {t.title} | Status: {t.status} | Specialist Required: {', '.join(t.specialist) if t.specialist else 'Triage Pending'}")
            return "\n".join(formatted)
            
    except Exception as e:
        return f"Error retrieving tickets: {str(e)}"

@tool
async def emergency(symptom: str) -> str:
    """
    Handles critical, life-threatening medical emergencies (e.g. chest pain, severe bleeding, breathing difficulties). Use this tool ONLY if the symptoms indicate high risk of urgent harm.
    """
    return (
        f"🚨 EMERGENCY WARNING: The symptom '{symptom}' you described indicates a potential medical emergency.\n\n"
        "Please follow these instructions immediately:\n"
        "1. CALL 911 (or your local emergency number) immediately.\n"
        "2. Do NOT attempt to drive yourself to the hospital; wait for an ambulance.\n"
        "3. Remain calm, sit or lie down, and stay in a safe environment.\n"
        "4. If you are with someone, notify them of your symptoms immediately."
    )



class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

class GradeHallucinations(BaseModel):
    """Binary score for hallucination check on generated answer."""
    binary_score: str = Field(description="Answer is grounded in the facts, 'yes' or 'no'")

class GradeAnswer(BaseModel):
    """Binary score to assess if answer addresses question."""
    binary_score: str = Field(description="Answer addresses the question, 'yes', 'fallback', or 'rewrite'")

@tool
async def check_relevance(query: str, documents: str) -> str:
    """Checks if the retrieved documents are relevant to the user's query."""
    system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains medical information related to the user's symptoms or question, grade it as relevant. \n
    It does not need to be a perfect match, just relevant enough to help form an answer. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    
    grader_llm = llm.with_structured_output(GradeDocuments)
    grade = await grader_llm.ainvoke([
        SystemMessage(content=system), 
        HumanMessage(content=f"Question: {query} \n\n Document: {documents}")
    ])
    return grade.binary_score

@tool
async def check_support(documents: str, generation: str) -> str:
    """Checks if a drafted answer is strictly grounded in the retrieved documents (hallucination check)."""
    system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved documents. \n 
    Medical accuracy is critical. If the answer contains information NOT present in the provided documents (hallucinations), grade it as 'no'.
    Give a binary score 'yes' or 'no'. 'yes' means that the answer is strictly grounded in / supported by the set of documents."""
    
    grader_llm = llm.with_structured_output(GradeHallucinations)
    grade = await grader_llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Set of documents: \n\n {documents} \n\n LLM generation: {generation}")
    ])
    return grade.binary_score

@tool
async def check_usefulness(query: str, generation: str) -> str:
    """Checks if the drafted answer addresses and resolves the user's query."""
    system = """You are a medical grader assessing whether an answer addresses / resolves a user question. \n 
    - 'yes': The answer resolves the question accurately and safely.
    - 'rewrite': The answer is partially relevant but lacks critical detail that might be found with a better search query.
    - 'fallback': The answer does not resolve the question and further searching our records is unlikely to help (e.g. out-of-scope medical question).
    """
    
    grader_llm = llm.with_structured_output(GradeAnswer)
    grade = await grader_llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=f"User question: \n\n {query} \n\n LLM generation: {generation}")
    ])
    return grade.binary_score

@tool
async def find_nearby_facility(location: str, facility_type: str = "hospital") -> str:
    """
    Finds the nearest medical facility based on a location string.
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{facility_type} near {location}",
            "format": "json",
            "limit": 3
        }
        headers = {"User-Agent": "AI-Medical-Triage-Hub/1.0"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            results = response.json()
            
        if not results:
            return f"I couldn't find any {facility_type}s near '{location}'."
            
        formatted = [
            "CRITICAL INSTRUCTION: You MUST show the following list to the user verbatim in your response. Do not summarize it. Preserve all markdown formatting.", 
            f"Here are the nearest {facility_type}s near {location}:\n\n"
        ]
        for place in results:
            name = place.get('name', 'Unknown Facility')
            address = place.get('display_name', 'Unknown Address')
            # Removing redundant name from the address if it starts with it
            if address.startswith(name + ", "):
                address = address[len(name) + 2:]
            
            formatted.append(f"🏥 {name}\n📍 {address}\n")
            
        return "\n".join(formatted)
        
    except Exception as e:
        return f"Error finding nearby facilities: {str(e)}"

tools = [search_medical_knowledge, create_ticket, list_tickets, emergency, find_nearby_facility]

@tool
async def analyze_closable_tickets(config: RunnableConfig) -> str:
    """
    Analyzes all open tickets assigned to the doctor and returns a list of tickets recommended for closure.
    Use this tool when the doctor asks to find tickets that can be closed.
    """
    try:
        user_id = config.get("configurable", {}).get("user_id")
        if not user_id:
            return "Error: You must be logged in as a doctor to use this tool."

        tickets = await Ticket.find(
            Ticket.assigned_to == PydanticObjectId(user_id),
            Ticket.status.nin(["completed", "Report Sent"])
        ).to_list()

        if not tickets:
            return "You have no open tickets."

        closable_tickets = []
        for ticket in tickets:
            if not ticket.channel_id:
                continue
            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(50).to_list()
            if not messages:
                continue
                
            formatted_messages = [{"user": {"name": m.sender_name}, "text": m.text} for m in messages]
            analysis = await analyze_ticket_chat_ai(formatted_messages)
            
            if analysis and analysis.get("recommendedStatus") != "In Progress":
                closable_tickets.append({
                    "id": str(ticket.id),
                    "title": ticket.title,
                    "reasoning": analysis.get("reasoning", "AI suggests closure based on chat history.")
                })

        if not closable_tickets:
            return "No tickets are currently recommended for closure based on AI analysis."

        formatted = ["CRITICAL INSTRUCTION: Show this list verbatim.", "Here are the tickets recommended for closure:"]
        for t in closable_tickets:
            formatted.append(f"- Ticket ID: {t['id']} | Title: {t['title']} | Reasoning: {t['reasoning']}")
        return "\n".join(formatted)

    except Exception as e:
        return f"Error analyzing tickets: {str(e)}"

@tool
async def close_ticket(ticket_id: str, config: RunnableConfig) -> str:
    """
    Closes a specific ticket and adds an AI-generated summary to the helpful notes.
    """
    try:
        user_id = config.get("configurable", {}).get("user_id")
        ticket = await Ticket.get(ticket_id)
        if not ticket:
            return f"Error: Ticket {ticket_id} not found."
            
        if str(ticket.assigned_to) != user_id:
            return f"Error: You are not authorized to close Ticket {ticket_id}."

        chat_history_text = ""
        if ticket.channel_id:
            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(50).to_list()
            chat_history_text = "\\n".join([f"{m.sender_name}: {m.text}" for m in messages])

        context = (ticket.helpful_notes or "") + "\\n\\nChat History:\\n" + chat_history_text
        summary = await generate_closure_summary(ticket.title, ticket.description, context)

        ticket.status = "completed"
        if ticket.helpful_notes:
            ticket.helpful_notes += f"\\n\\n[CLOSURE]: {summary}"
        else:
            ticket.helpful_notes = f"[CLOSURE]: {summary}"

        await ticket.save()
        return f"Ticket {ticket_id} successfully closed. Summary added."

    except Exception as e:
        return f"Error closing ticket {ticket_id}: {str(e)}"

@tool
async def generate_report(ticket_id: str, config: RunnableConfig) -> str:
    """
    Generates a SOAP note report for a specific ticket and sends it to the admin.
    """
    try:
        user_id = config.get("configurable", {}).get("user_id")
        ticket = await Ticket.get(ticket_id)
        if not ticket:
            return f"Error: Ticket {ticket_id} not found."
            
        if ticket.status != "completed":
            return f"Error: Ticket {ticket_id} must be closed before generating a report."

        chat_transcript = ""
        if ticket.channel_id:
            messages = await ChatMessage.find(ChatMessage.ticket_id == PydanticObjectId(ticket.id)).sort("created_at").limit(100).to_list()
            chat_transcript = "\\n".join([f"{m.sender_name}: {m.text}" for m in messages])

        triage_content = await generate_soap_note(ticket.title, ticket.description, chat_transcript)
        if not triage_content:
            triage_content = {
                "subjective": f"Complaint: {ticket.title}\\n{ticket.description}",
                "objective": "None reported",
                "assessment": "Pending AI analysis",
                "plan": "Follow up required"
            }

        formatted_report = f"**SUBJECTIVE**: {triage_content.get('subjective', '')}\\n**OBJECTIVE**: {triage_content.get('objective', '')}\\n**ASSESSMENT**: {triage_content.get('assessment', '')}\\n**PLAN**: {triage_content.get('plan', '')}"

        triage_content['ticket_id'] = str(ticket.id)
        triage_content['doctor_id'] = str(user_id)

        report = Report(
            content=triage_content,
            formatted_report=formatted_report,
            ticket_id=str(ticket.id)
        )
        await report.insert()

        ticket.status = "Report Sent"
        await ticket.save()

        # Trigger embedding asynchronously
        asyncio.create_task(generate_embedding(f"Subjective: {triage_content.get('subjective')}\\nObjective: {triage_content.get('objective')}\\nAssessment: {triage_content.get('assessment')}"))

        return f"Report generated and sent for ticket {ticket_id} successfully."

    except Exception as e:
        return f"Error generating report for ticket {ticket_id}: {str(e)}"