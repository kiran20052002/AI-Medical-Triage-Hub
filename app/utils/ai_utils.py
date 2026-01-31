import os
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


groq_api_key = os.getenv("GROQ_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")

embeddings = None
if gemini_api_key:
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=gemini_api_key)
    except Exception as e:
        print(f"Embeddings initialization failed: {e}")

llm = None
if groq_api_key:
    llm = ChatGroq(temperature=0, model_name="llama-3.1-8b-instant", groq_api_key=groq_api_key)


# Pydantic Models for parsers
class TicketAnalysis(BaseModel):
    summary: str = Field(description="A short 1-2 sentence summary of the issue.")
    priority: str = Field(description="One of 'low', 'medium', or 'high'.")
    helpfulNotes: str = Field(description="A detailed medical explanation that a doctor can use to help this patient. Include useful external links or resources if possible.")
    specialist: List[str] = Field(description="An array of relevant specialists required to solve the issue (e.g., ['Cardiologist', 'Dermatologist', 'General Physician']).")

class ChatAnalysis(BaseModel):
    recommendedStatus: str = Field(description="One of 'In Progress' or 'Completed'.")
    confidence: float = Field(description="Confidence score between 0 and 100.")
    reasoning: str = Field(description="A short explanation of why this status is recommended.")

class TriageReport(BaseModel):
    chief_complaint: str = Field(description="The patient's primary issue, history, and story (Subjective).")
    symptoms_observations: str = Field(description="Specific symptoms extracted from chat, or observations from reported photos. Example: 'Fever 38C', 'Redness on left arm'.")
    triage_assessment: str = Field(description="AI's analysis of the urgency and potential medical area (Assessment).")
    recommended_plan: str = Field(description="Suggested next steps (e.g., 'Go to ER', 'See GP') and immediate home care advice (Plan).")


async def analyze_ticket_ai(title: str, description: str):
    if not llm:
        print("AI Analysis Skipped: No LLM initialized.")
        return None
    
    parser = JsonOutputParser(pydantic_object=TicketAnalysis)

    prompt = PromptTemplate(
        template="""You are a medical triage agent.
        Analyse the following ticket (patient request).

        Ticket information:
        - Title: {title}
        - Description: {description}

        {format_instructions}
        """,
        input_variables=["title","description"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        result = await chain.invoke({"title": title, "description": description})
        return result
    except Exception as e:
        print(f"AI Analysis Failed: {e}")
        return None


async def analyze_ticket_chat_ai(messages: List[Dict]):
    if not llm:
        return {"recommendedStatus": "in_progress", "confidence": 0, "reasoning": "No LLM initialized."}
    

    conversation = "\n".join([f"{m.get('user', {}).get('name', 'User')}: {m.get('text')}" for m in messages])

    parser = JsonOutputParser(pydantic_object=ChatAnalysis)

    prompt = PromptTemplate(
        template = """ Analyze this conversation and recommend if the ticket should closed.
        
        Conversation:
        {conversation}

        {format_instructions}
        """,
        input_variables=["conversation"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"conversation": conversation})
        return result
    
    except Exception as e:
        print(f"Chat Analysis Failed: {e}")
        return {
            "recommendedStatus": "in_progress",
            "confidence": 0,
            "reasoning": "AI analysis failed."
        }



async def generate_closure_summary(title: str, description: str, history: str = "") -> str:
    """
    Generates a closing summary for a ticket.
    """
    if not llm:
        return "Ticket closed manually. No AI summary available."
    
    prompt = f"""You are a medical assistant closing a support ticket.
    Generate a professional, concise closing note summarizing the case and the action taken.
    
    Ticket: {title}
    Description: {description}
    Additional Context: {history}
    
    Return ONLY the closing note text.
    """

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        print(f"Closure Summary Failed: {e}")
        return "Ticket closed. (AI Summary Failed)"




async def generate_embedding(text: str) -> List[float]:
    if not embeddings:
        return []
    
    try:
        return await embeddings.aembed_query(text)
    
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return []



async def generate_triage_report(title: str, description: str, chat_histroy: str) -> Optional[dict]:
    """
    Generates a Clinical Triage Report from ticket info and chat history.
    """
    if not llm:
        return None
    
    parser = JsonOutputParser(pydantic_object=TriageReport)

    prompt = PromptTemplate(
        template="""You are an expert Medical AI Assistant. Your task is to generate a professional Clinical Triage Report from a patient-doctor chat transcript.
        
        Ticket Info:
        Title: {title}
        Desc: {description}
        
        Chat Transcript:
        {chat_history}
        
        {format_instructions}
        """,
        input_variables=["title", "description", "chat_history"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    ) 

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"title": title, "description": description, "chat_history": chat_history})
        return result
    
    except Exception as e:
        print(f"Triage Report Generation Failed: {e}")
        return None
