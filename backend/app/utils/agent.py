import operator
from typing import Annotated, List, TypedDict, Union
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.utils.ai_utils import llm, generate_medical_response
from app.utils.tools import search_medical_records
from pydantic import BaseModel, Field

# 1. State Definition
class AgentState(TypedDict):
    query: str
    messages: Annotated[List[BaseMessage], operator.add]
    documents: str
    retry_count: int
    response: str
    mode: str # 'generate_direct', 'retrieve', 'rewrite', 'nosimilar'
    hallucination_score: str # 'yes' or 'no'
    answer_score: str # 'yes' or 'no'

# 2. Pydantic models for structured output
class RouteQuery(BaseModel):
    """Route a user query to the most relevant datasource."""
    datasource: str = Field(
        description="Given a user question choose to route it to 'retrieve' or 'generate_direct'. Use 'retrieve' ONLY if the user specifically asks for past similar records or cases. Otherwise use 'generate_direct'.",
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

# 3. Nodes
def decide_retrieval_node(state: AgentState):
    """
    Determines whether to retrieve from vector store or generate a direct response.
    """
    print("--- DECIDE RETRIEVAL NODE ---")
    messages = state["messages"]
    last_message = messages[-1].content
    
    system = """You are an expert medical router. 
    Analyze the user's medical query and decide if it needs database retrieval.
    - 'retrieve': The user is specifically asking for past similar cases, historical medical records, or "people like me" experiences.
    - 'generate_direct': Everything else, including greetings, general medical questions, or emergencies.
    """
    
    router_llm = llm.with_structured_output(RouteQuery)
    route = router_llm.invoke([SystemMessage(content=system)] + messages)
    
    return {"mode": route.datasource}

def generate_direct_node(state: AgentState):
    """
    Handles queries that don't need retrieval: emergencies, clarifications, and general medical info.
    """
    print("--- GENERATE DIRECT NODE ---")
    messages = state["messages"]
    
    system = """You are a helpful and empathetic medical assistant.
    1. If the query indicates an EMERGENCY (chest pain, severe bleeding, etc.), give immediate instructions to call 911.
    2. If the query is too vague (e.g. "I'm sick"), ask a follow-up question.
    3. Otherwise, provide a polite and helpful medical response based on your general knowledge.
    """
    
    response = llm.invoke([SystemMessage(content=system)] + messages)
    return {"response": response.content, "messages": [response]}


def retriever_node(state: AgentState):
    print("--- RETRIEVER NODE ---")
    messages = state["messages"]
    query = messages[-1].content
    # Call the tool directly for simplicity in the graph node
    docs = search_medical_records.invoke(query)
    return {"documents": docs, "retry_count": state.get("retry_count", 0)}

def is_relevant_node(state: AgentState):
    print("--- IS RELEVANT NODE ---")
    messages = state["messages"]
    query = messages[-1].content
    docs = state["documents"]
    
    if "No matching medical records" in docs or "Error" in docs:
        return {"mode": "nosimilar"}

    system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
    If the document contains medical information related to the user's symptoms or question, grade it as relevant. \n
    It does not need to be a perfect match, just relevant enough to help form an answer. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
    
    grader_llm = llm.with_structured_output(GradeDocuments)
    grade = grader_llm.invoke([
        SystemMessage(content=system), 
        HumanMessage(content=f"Question: {query} \n\n Document: {docs}")
    ])
    
    if grade.binary_score == "yes":
        return {"mode": "generate"}
    else:
        return {"mode": "nosimilar"}

def rewrite_question_node(state: AgentState):
    print("--- REWRITE QUESTION NODE ---")
    messages = state["messages"]
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 2:
        return {"mode": "nosimilar"}
    
    system = "You are a medical query optimizer. The previous search failed to find relevant records. Rephrase the user's query to be more technical and descriptive for a better medical database search match. Return ONLY the new query string."
    new_query = llm.invoke([SystemMessage(content=system)] + messages)
    
    # We update the query for the tool by returning a special message but it's easier to just return the string if needed.
    # However, for consistency we'll just return the query string in the state metadata.
    return {"query": new_query.content, "retry_count": retry_count + 1, "mode": "retrieve"}

def generate_from_context_node(state: AgentState):
    print("--- GENERATE FROM CONTEXT NODE ---")
    messages = state["messages"]
    docs = state["documents"]
    
    system_prompt = f"""You are a helpful and empathetic medical assistant.
    Your goal is to answer the patient's question based ONLY on the provided Context (which comes from a database of similar past medical cases).
    
    Rules:
    1. BE CONCISE AND DIRECT.
    2. NEVER say "Based on your medical records" or "Your history shows". Instead, use "Based on similar past cases" or "Our database suggests".
    3. DO NOT offer follow-up questions.
    4. If the Context DOES NOT contain a relevant answer, strictly say: "I couldn't find a similar case in our records. Please create a support ticket for further assistance."
    5. Do not make up medical advice.
    
    CONTEXT (SIMILAR PAST CASES):
    {docs}
    """
    
    response = llm.invoke([SystemMessage(content=system_prompt)] + messages)
    return {"response": response.content, "messages": [response]}

def no_answer_found_node(state: AgentState):
    print("--- NO ANSWER FOUND NODE ---")
    response = "I've searched our medical records and couldn't find a case similar to your description. I recommend creating a support ticket so one of our specialists can review your symptoms in detail."
    return {"response": response}

def is_sup_node(state: AgentState):
    """
    Determines whether the generation is grounded in the document and not hallucinating.
    """
    print("--- IS SUP NODE ---")
    docs = state["documents"]
    generation = state["response"]
    
    if "I couldn't find a similar case in our records" in generation:
        return {"hallucination_score": "no"} # Treat as "grounded" but leads to no_answer flow later

    system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved documents. \n 
    Give a binary score 'yes' or 'no'. 'yes' means that the answer is grounded in / supported by the set of documents."""
    
    grader_llm = llm.with_structured_output(GradeHallucinations)
    grade = grader_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Set of documents: \n\n {docs} \n\n LLM generation: {generation}")
    ])

    return {"hallucination_score": grade.binary_score}

def revise_answer_node(state: AgentState):
    """
    Revises the answer if hallucinations are detected.
    """
    print("--- REVISE ANSWER NODE ---")
    messages = state["messages"]
    docs = state["documents"]
    response = state["response"]
    
    system = f"""You are a medical response reviser. The previous response was found to have hallucinations or was not fully grounded in the context.
    Rewrite the answer to be strictly supported by the provided Context.
    
    CONTEXT:
    {docs}
    
    PREVIOUS RESPONSE:
    {response}
    """
    
    revised_response = llm.invoke([SystemMessage(content=system)] + messages)
    return {"response": revised_response.content, "messages": [revised_response]}

def is_use_node(state: AgentState):
    """
    Determines whether the generation addresses the question.
    """
    print("--- IS USE NODE ---")
    messages = state["messages"]
    query = messages[0].content # Use the original query for grounding
    generation = state["response"]
    retry_count = state.get("retry_count", 0)

    system = """You are a grader assessing whether an answer addresses / resolves a user question. \n 
    Give a score:
    - 'yes': The answer resolves the question.
    - 'rewrite': The answer is relevant but the query could be better to get a more precise answer.
    - 'fallback': The answer does not resolve the question and further search is unlikely to help.
    """
    
    grader_llm = llm.with_structured_output(GradeAnswer)
    grade = grader_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"User question: \n\n {query} \n\n LLM generation: {generation}")
    ])
    
    # Logic to limit retries for 'rewrite'
    if grade.binary_score == "rewrite" and retry_count >= 2:
        return {"answer_score": "fallback"}

    return {"answer_score": grade.binary_score}

# 4. Graph Construction
def create_agent_graph(checkpointer=None):
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("decide_retrieval", decide_retrieval_node)
    workflow.add_node("generate_direct", generate_direct_node)
    workflow.add_node("retrieve", retriever_node)
    workflow.add_node("is_relevant", is_relevant_node)
    workflow.add_node("generate_from_context", generate_from_context_node)
    workflow.add_node("is_sup", is_sup_node)
    workflow.add_node("revise_answer", revise_answer_node)
    workflow.add_node("is_use", is_use_node)
    workflow.add_node("rewrite_question", rewrite_question_node)
    workflow.add_node("no_answer_found", no_answer_found_node)
    
    # Define Edges
    workflow.set_entry_point("decide_retrieval")
    
    workflow.add_conditional_edges(
        "decide_retrieval",
        lambda x: x["mode"],
        {
            "retrieve": "retrieve",
            "generate_direct": "generate_direct"
        }
    )
    
    workflow.add_edge("generate_direct", END)
    workflow.add_edge("retrieve", "is_relevant")
    
    workflow.add_conditional_edges(
        "is_relevant",
        lambda x: x["mode"],
        {
            "generate": "generate_from_context",
            "nosimilar": "no_answer_found"
        }
    )
    
    workflow.add_edge("generate_from_context", "is_sup")
    
    workflow.add_conditional_edges(
        "is_sup",
        lambda x: "grounded" if x["hallucination_score"] == "yes" else "hallucination",
        {
            "grounded": "is_use",
            "hallucination": "revise_answer"
        }
    )
    
    workflow.add_edge("revise_answer", "is_sup")
    
    workflow.add_conditional_edges(
        "is_use",
        lambda x: x["answer_score"],
        {
            "yes": END,
            "rewrite": "rewrite_question",
            "fallback": "no_answer_found"
        }
    )
    
    workflow.add_conditional_edges(
        "rewrite_question",
        lambda x: x["mode"],
        {
            "retrieve": "retrieve",
            "nosimilar": "no_answer_found"
        }
    )
    
    workflow.add_edge("no_answer_found", END)
    
    # Initialize Checkpointer if provided
    return workflow.compile(checkpointer=checkpointer)
