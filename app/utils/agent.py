import operator
from typing import Annotated, List, TypedDict, Union
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, StateGraph
from app.utils.ai_utils import llm, generate_medical_response
from app.utils.tools import search_medical_records
from pydantic import BaseModel, Field

# 1. State Definition
class AgentState(TypedDict):
    query: str
    documents: str
    retry_count: int
    response: str
    mode: str # 'emergency', 'clarify', 'search', 'generate'

# 2. Pydantic models for structured output
class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: str = Field(
        description="Given a user question choose to route it to 'emergency', 'clarify', or 'search'.",
    )

class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(description="Documents are relevant to the question, 'yes' or 'no'")

# 3. Nodes
async def router_node(state: AgentState):
    """
    Determines the next step based on the query.
    """
    print("--- ROUTER NODE ---")
    query = state["query"]
    
    system = """You are an expert medical router. 
    Analyze the user's medical query and classify it into one of these categories:
    - 'emergency': Life-threatening symptoms (chest pain, severe bleeding, difficulty breathing, unconsciousness).
    - 'clarify': The query is too vague to be useful (e.g., 'it hurts', 'help me').
    - 'search': A specific medical question or symptom description that can be searched in records.
    """
    
    router_llm = llm.with_structured_output(RouteQuery)
    route = await router_llm.ainvoke([SystemMessage(content=system), HumanMessage(content=query)])
    
    return {"mode": route.datasource}

async def emergency_node(state: AgentState):
    print("--- EMERGENCY NODE ---")
    response = "⚠️ **EMERGENCY DETECTED**: Please call 911 or your local emergency services immediately. Your symptoms suggest a potentially life-threatening situation that requires urgent professional medical attention."
    return {"response": response}

async def clarify_node(state: AgentState):
    print("--- CLARIFY NODE ---")
    query = state["query"]
    system = "You are a helpful medical assistant. The patient's query is too vague. Ask a polite follow-up question to get more details about their symptoms so you can help them better."
    resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=query)])
    return {"response": resp.content}

async def retriever_node(state: AgentState):
    print("--- RETRIEVER NODE ---")
    query = state["query"]
    # Call the tool directly for simplicity in the graph node
    docs = await search_medical_records.ainvoke(query)
    return {"documents": docs, "retry_count": state.get("retry_count", 0)}

async def grader_node(state: AgentState):
    print("--- GRADER NODE ---")
    query = state["query"]
    docs = state["documents"]
    
    if "No matching medical records" in docs or "Error" in docs:
        return {"mode": "transform"}

    system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains medical information related to the user's symptoms or question, grade it as relevant. \n
    It does not need to be a perfect match, just relevant enough to help form an answer. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    
    grader_llm = llm.with_structured_output(GradeDocuments)
    grade = await grader_llm.ainvoke([
        SystemMessage(content=system), 
        HumanMessage(content=f"Question: {query} \n\n Document: {docs}")
    ])
    
    if grade.binary_score == "yes":
        return {"mode": "generate"}
    else:
        return {"mode": "transform"}

async def transform_query_node(state: AgentState):
    print("--- TRANSFORM QUERY NODE ---")
    query = state["query"]
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 2:
        return {"mode": "fallback"}
    
    system = "You are a medical query optimizer. The previous search failed to find relevant records. Rephrase the user's query to be more technical and descriptive for a better medical database search match. Return ONLY the new query string."
    new_query = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=query)])
    
    return {"query": new_query.content, "retry_count": retry_count + 1, "mode": "search"}

async def generator_node(state: AgentState):
    print("--- GENERATOR NODE ---")
    query = state["query"]
    docs = state["documents"]
    
    system_prompt = f"""You are a helpful and empathetic medical assistant.
    Your goal is to answer the patient's question based ONLY on the provided Context (which comes from a database of similar past medical cases).
    
    Rules:
    1. BE CONCISE AND DIRECT. Provide the solution or medical guidance immediately.
    2. NEVER say "Based on your medical records" or "Your history shows". Instead, use "Based on similar past cases" or "Our database suggests".
    3. DO NOT offer follow-up questions like "Would you like more info?". Just give the answer.
    4. If the Context DOES NOT contain a relevant answer, strictly say: "I couldn't find a similar case in our records. Please create a support ticket for further assistance."
    5. Do not make up medical advice. Use only the provided context.
    6. EXCLUDE all phrases about scheduling, checking back, or acting as a doctor.
    
    CONTEXT (SIMILAR PAST CASES):
    {docs}
    """
    
    response = await generate_medical_response(system_prompt, query)
    return {"response": response}

async def fallback_node(state: AgentState):
    print("--- FALLBACK NODE ---")
    response = "I've searched our medical records and couldn't find a case similar to your description. I recommend creating a support ticket so one of our specialists can review your symptoms in detail."
    return {"response": response}

# 4. Graph Construction
def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("emergency", emergency_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("retrieve", retriever_node)
    workflow.add_node("grade", grader_node)
    workflow.add_node("transform", transform_query_node)
    workflow.add_node("generate", generator_node)
    workflow.add_node("fallback", fallback_node)
    
    # Define Edges
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges(
        "router",
        lambda x: x["mode"],
        {
            "emergency": "emergency",
            "clarify": "clarify",
            "search": "retrieve"
        }
    )
    
    workflow.add_edge("emergency", END)
    workflow.add_edge("clarify", END)
    
    workflow.add_edge("retrieve", "grade")
    
    workflow.add_conditional_edges(
        "grade",
        lambda x: x["mode"],
        {
            "generate": "generate",
            "transform": "transform"
        }
    )
    
    workflow.add_conditional_edges(
        "transform",
        lambda x: x["mode"],
        {
            "search": "retrieve",
            "fallback": "fallback"
        }
    )
    
    workflow.add_edge("generate", END)
    workflow.add_edge("fallback", END)
    
    return workflow.compile()

# Initialize the graph
agent_executor = create_agent_graph()
