import operator
from typing import Annotated, List, TypedDict, Union
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_core.tools import tool
from app.utils.ai_utils import llm
from app.utils.tools import tools, create_ticket, list_tickets, emergency, search_medical_knowledge, check_relevance, check_support, check_usefulness, find_nearby_facility
from langchain_core.runnables.config import RunnableConfig


class AgentState(TypedDict):
    query: str
    messages: Annotated[List[BaseMessage], operator.add]
    documents: List[str]
    retry_count: int
    response: str
    mode: str
    hallucination_score: str 
    answer_score: str



rag_system_prompt = """You are a meticulous medical research agent. Your goal is to answer the user's question by searching our database of similar past medical cases. You must strictly follow this process:

1. **Search**: Use the provided search tool to find relevant past cases based on the user's query.
2. **Check Relevance**: Use the relevance checking tool to verify if the retrieved documents are relevant to the user's question. 
   - If they are NOT relevant, rewrite your search query and try searching again. You have a MAXIMUM limit of 2 search attempts/rewrites. 
   - If you reach the limit or still cannot find relevant documents, output exactly: "I've searched our medical records and couldn't find a case similar to your description. I recommend creating a support ticket so one of our specialists can review your symptoms in detail." and stop.
3. **Draft & Check Support**: If relevant documents are found, draft a concise and direct answer based ONLY on the retrieved documents. NEVER say "Based on your medical records"; instead use "Based on similar past cases". Do not offer follow-up questions. 
   - Before providing the answer to the user, you MUST use the support checking tool to verify your draft is strictly grounded in the retrieved documents (no hallucinations). 
   - If it returns 'no', revise your draft and check again. You have a MAXIMUM limit of 2 drafting attempts. If you reach the limit and it still fails, output the standard fallback message mentioned above.
4. **Check Usefulness**: Use the usefulness checking tool to ensure your drafted answer actually resolves the user's question. 
   - If it returns 'rewrite', and you have not exceeded your 2 search limit, try searching again with a better query. 
   - If it returns 'fallback' or you have hit your search limit, output the standard fallback message.

OUTPUT FORMAT:
If you find relevant documents and successfully draft an answer, you MUST append a "Sources:" section at the very end of your final response listing the exact names of the source documents (found in the 'Source:' tag of the retrieved results). 
Example format:
[Your Answer Here]

Sources:
- DocumentName.pdf - Part 1

Only once your drafted answer passes all checks ('yes' for relevance, 'yes' for support, and 'yes' for usefulness) should you output the final answer to the user.
"""

rag_agent_app = create_react_agent(
    llm, 
    tools=[search_medical_knowledge, check_relevance, check_support, check_usefulness], 
    prompt=rag_system_prompt
)

async def call_rag_agent(state: AgentState, config: RunnableConfig):
    print("--- CALL RAG SUB-AGENT ---")
    messages = state["messages"]
    last_message = messages[-1]
    
    # We strip the last message (which contains the un-executed tool call) 
    # so the RAG agent starts clean from the user's prompt.
    clean_messages = messages[:-1]
    
    response = await rag_agent_app.ainvoke({"messages": clean_messages}, config)
    rag_final_text = response["messages"][-1].content
    
    # Manually extract sources and append them if the LLM forgot
    sources = set()
    import re
    for msg in response["messages"]:
        if isinstance(msg, ToolMessage) and msg.name == "search_medical_knowledge":
            matches = re.findall(r"--- Source: (.*?) ---", msg.content)
            for m in matches:
                sources.add(m)
                
    if sources and "Sources:" not in rag_final_text:
        rag_final_text += "\n\n**Sources:**\n" + "\n".join([f"- {s}" for s in sources])
    
    # We MUST fulfill the main agent's tool call to avoid INVALID_CHAT_HISTORY errors
    tool_call_id = last_message.tool_calls[0]["id"]
    tool_message = ToolMessage(
        content=rag_final_text, 
        tool_call_id=tool_call_id, 
        name="search_medical_knowledge"
    )
    
    # We also return a standard AIMessage so the UI displays the response correctly
    final_ai_message = AIMessage(content=rag_final_text)
    
    return {"messages": [tool_message, final_ai_message]}



async def agent_node(state: AgentState, config: RunnableConfig):
    print("--- AGENT NODE ---")
    messages = state["messages"]
    
    llm_with_tools = llm.bind_tools(tools)
    
    system = """You are a helpful and empathetic medical assistant.
You have access to several tools.
CRITICAL: If the user asks ANY medical question or describes ANY symptoms, you MUST use the search_medical_knowledge tool to search for medical documents. Do NOT answer from your own knowledge.

IMPORTANT: When you use the find_nearby_facility tool, you MUST explicitly list the names and addresses of the facilities returned by the tool in your final response. Do not just output a generic disclaimer.

If no tools are needed (e.g. greetings, general conversation, or follow-up clarifications), write a direct answer.

CRITICAL: If a tool execution returns a cancellation or rejection response (for example, if the create_ticket tool returns "Ticket creation cancelled by user."), do NOT call that tool again in this turn. Instead, write a direct text response to the user acknowledging the cancellation and asking how they would like to proceed.
"""
    
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    msgs_to_run = messages if has_system else [SystemMessage(content=system)] + messages
    
    response = await llm_with_tools.ainvoke(msgs_to_run, config)
    return {"messages": [response]}


async def direct_answer_node(state: AgentState):
    print("--- DIRECT ANSWER NODE ---")
    messages = state["messages"]
    last_message = messages[-1]
    return {"response": last_message.content}


def route_after_agent(state: AgentState):
    print("--- ROUTE AFTER AGENT ---")
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name == "search_medical_knowledge":
            return "call_rag_agent"
        else:
            return "other_tools"
            
    return "direct_answer"


def create_agent_graph(checkpointer=None):
    """
    Compiles the main agent graph with human approval capability.
    """
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("other_tools", ToolNode([create_ticket, list_tickets, emergency, find_nearby_facility]))
    workflow.add_node("call_rag_agent", call_rag_agent)
    workflow.add_node("direct_answer", direct_answer_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "call_rag_agent": "call_rag_agent",
            "other_tools": "other_tools",
            "direct_answer": "direct_answer"
        }
    )
    
    workflow.add_edge("other_tools", "agent")
    workflow.add_edge("call_rag_agent", END)
    workflow.add_edge("direct_answer", END)
    
    return workflow.compile(checkpointer=checkpointer)