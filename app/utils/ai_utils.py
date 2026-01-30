import os
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


groq_api_key = os.getenv("GROQ_API_KEY")

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
