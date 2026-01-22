import os
from typing import List, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
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

    

