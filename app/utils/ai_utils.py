import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

load_dotenv()

# Initialize LangChain Models
gemini_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")


# Initialize Google GenAI Client
client = None
if gemini_api_key:
    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)
    except ImportError:
        print("Error: google-genai library not installed.")
    except Exception as e:
        print(f"Warning: Failed to init Gemini Client: {e}")

llm = None
if groq_api_key:
    llm = ChatGroq(
        temperature=0,
        model_name="llama-3.1-8b-instant",
        groq_api_key=groq_api_key
    )

# Pydantic Models for parsers 
class TicketAnalysis(BaseModel):
    summary: str = Field(description="A short 1-2 sentence summary of the issue.")
    priority: str = Field(description="One of 'low', 'medium', or 'high'.")
    helpfulNotes: str = Field(description="A detailed medical explanation that a doctor can use to help this patient. Include useful external links or resources if possible.")
    specialist: List[str] = Field(description="An array of relevant specialists required to solve the issue (e.g., ['Cardiologist', 'Dermatologist', 'General Physician']).")

class ChatAnalysis(BaseModel):
    recommendedStatus: str = Field(description="One of 'completed' or 'in_progress'.")
    confidence: float = Field(description="Confidence score between 0 and 100.")
    reasoning: str = Field(description="Brief explanation for the recommendation.")

class QueryClassification(BaseModel):
    is_valid: bool = Field(description="True if the query describes a reasonably valid medical situation, symptom, or question. False if it is gibberish (e.g., 'abcd'), completely unrelated to health, or too short to be meaningful.")
    reason: str = Field(description="Brief explanation of the classification.")



async def analyze_ticket_ai(title: str, description: str):
    if not llm:
        print("AI Analysis Skipped: No LLM initialized.")
        return None

    parser = JsonOutputParser(pydantic_object=TicketAnalysis)

    prompt = PromptTemplate(
        template="""You are a medical triage agent.
        Analyze the following support ticket (patient request).
        
        Ticket information:
        - Title: {title}
        - Description: {description}
        
        {format_instructions}
        """,
        input_variables=["title", "description"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"title": title, "description": description})
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

async def classify_medical_query(query: str) -> Optional[dict]:
    """
    Classifies a user query to see if it is a valid medical inquiry or gibberish/spam.
    """
    if not llm:
        return {"is_valid": True, "reason": "No LLM configured."}
        
    parser = JsonOutputParser(pydantic_object=QueryClassification)
    
    prompt = PromptTemplate(
        template="""You are a triage screening agent. Analyze the following user message:
        "{query}"
        
        Determine if this is a valid medical concern. 
        - Valid means it describes a symptom, medical question, pain, or health issue (even if brief, like "headache").
        - Invalid means it is gibberish (e.g., "abcd", "asdf"), random characters, pure spam, or a completely non-health question (e.g., "how to code").
        
        {format_instructions}
        """,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    chain = prompt | llm | parser
    
    try:
        result = await chain.ainvoke({"query": query})
        return result
    except Exception as e:
        print(f"Query Classification Failed: {e}")
        return {"is_valid": True, "reason": "Classification failed, allowing query."}

async def generate_embedding(text: str) -> List[float]:
    if not client:
        raise Exception("Google GenAI Client is not initialized (missing API key or library).")
    
    result = client.models.embed_content(
        model="models/text-embedding-004",
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