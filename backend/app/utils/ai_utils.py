import os
import io
import pymupdf
import asyncio
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models import MedicalDocumentParent, MedicalDocumentChunk
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

load_dotenv()


gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")



client = None
if gemini_api_key:
    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)
    except ImportError:
        print("Error: google-genai library not installed.")
    except Exception as e:
        print(f"Warning: Failed to init Gemini Client: {e}")

from langchain_google_genai import ChatGoogleGenerativeAI

llm = None
if groq_api_key:
    llm = ChatGroq(
        temperature=0,
        model_name="openai/gpt-oss-20b",
        groq_api_key=groq_api_key
    )
elif gemini_api_key:
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        temperature=0,
        google_api_key=gemini_api_key
    )


class TicketAnalysis(BaseModel):
    summary: str = Field(description="A short 1-2 sentence summary of the issue.")
    priority: str = Field(description="One of 'low', 'medium', or 'high'.")
    helpfulNotes: str = Field(description="A detailed medical explanation that a doctor can use to help this patient. Include useful external links or resources if possible.")
    specialist: List[str] = Field(description="An array of relevant specialists required to solve the issue (e.g., ['Cardiologist', 'Dermatologist', 'General Physician']).")

class ChatAnalysis(BaseModel):
    recommendedStatus: str = Field(description="One of 'completed' or 'in_progress'.")
    confidence: float = Field(description="Confidence score between 0 and 100.")
    reasoning: str = Field(description="Brief explanation for the recommendation.")



async def analyze_ticket_ai(title: str, description: str, available_specialists: Optional[List[str]] = None):
    if not llm:
        print("AI Analysis Skipped: No LLM initialized.")
        return None

    parser = JsonOutputParser(pydantic_object=TicketAnalysis)

    specialists_str = ""
    if available_specialists:
        specialists_str = f"Available Specialists (YOU MUST SELECT FROM THESE): {', '.join(available_specialists)}"

    prompt = PromptTemplate(
        template="""You are a medical triage agent.
        Analyze the following support ticket (patient request).
        
        Ticket information:
        - Title: {title}
        - Description: {description}
        
        {specialists_str}

        {format_instructions}
        """,
        input_variables=["title", "description", "specialists_str"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"title": title, "description": description, "specialists_str": specialists_str})
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
        template="""Analyze this conversation and recommend if the ticket should be closed.
        
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

async def generate_embedding(text: str) -> List[float]:
    if not client:
        raise Exception("Google GenAI Client is not initialized (missing API key or library).")
    
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values

async def generate_medical_response(system_prompt: str, user_query: str) -> str:
    """
    Generates a response for the medical chatbot using the provided system prompt and user query.
    Used by the chatbot router.
    """
    if not llm:
        raise Exception("LLM is not initialized (missing Groq API key).")
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'Patient Query: "{user_query}"')
    ]
    
    response = await llm.ainvoke(messages)
    return response.content

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

class SOAPNote(BaseModel):
    subjective: str = Field(description="Summarize patient's complaints, history, and symptoms.")
    objective: str = Field(description="List direct observations from photos or exams mentioned in chat. IF NO PHOTOS/EXAMS, explicitly write 'None reported'.")
    assessment: str = Field(description="Likely diagnosis based on symptoms.")
    plan: str = Field(description="Treatment, tests ordered, and follow-up advice.")

async def generate_soap_note(title: str, description: str, chat_history: str) -> Optional[dict]:
    """
    Generates a SOAP note from ticket info and chat history.
    """
    if not llm:
        return None
        
    parser = JsonOutputParser(pydantic_object=SOAPNote)

    prompt = PromptTemplate(
        template="""You are an expert Medical AI Assistant. Your task is to generate a professional SOAP note (Subjective, Objective, Assessment, Plan) from a patient-doctor chat transcript.
        
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
        print(f"SOAP Generation Failed: {e}")
        return None

async def process_medical_pdf(file_bytes: bytes, filename: str):
    """
    Parses a PDF, chunks it using a parent-child strategy, generates embeddings for child chunks,
    and stores them in MongoDB.
    """
    
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
        
    doc.close()

    if not full_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    parent_texts = parent_splitter.split_text(full_text)


    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )

    for i, p_text in enumerate(parent_texts):
        parent_doc = MedicalDocumentParent(
            title=f"{filename} - Part {i+1}",
            content=p_text
        )
        await parent_doc.insert()

        child_texts = child_splitter.split_text(p_text)
        
        for c_text in child_texts:
            embedding = await generate_embedding(c_text)
            
            child_doc = MedicalDocumentChunk(
                parent_id=parent_doc.id,
                content=c_text,
                embedding=embedding
            )
            await child_doc.insert()
            
    return {"message": f"Successfully processed {len(parent_texts)} parent chunks and their child chunks."}
