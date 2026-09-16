import operator
from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from app.utils.ai_utils import llm
from app.utils.tools import analyze_closable_tickets, close_ticket, generate_report, list_tickets
from langchain_core.runnables.config import RunnableConfig

class DoctorAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

doctor_tools = [analyze_closable_tickets, close_ticket, generate_report, list_tickets]

async def doctor_agent_node(state: DoctorAgentState, config: RunnableConfig):
    print("--- DOCTOR AGENT NODE ---")
    messages = state["messages"]
    
    llm_with_tools = llm.bind_tools(doctor_tools)
    
    system = """You are a specialized medical AI assistant for doctors at the AI Medical Triage Hub.
You must NEVER mention that you are an AI developed by OpenAI, ChatGPT, or any other specific corporate entity. If asked who you are, simply state that you are the AI Medical Triage Hub Assistant.
You have access to the following tools:
- `analyze_closable_tickets`: Use this to scan the doctor's still-open tickets (it automatically excludes already-closed ones), identify which are recommended for closure, and present them to the doctor through a human-in-the-loop approval UI. The doctor selects exactly which of the recommended tickets to close in that UI; this tool then closes only those selected tickets and generates their reports. It handles the doctor's confirmation itself — you do not need to ask the doctor to confirm separately.
- `close_ticket`: Use this ONLY when the doctor directly names one specific ticket ID/ticket to close in their message (a single, explicit request). Do not use it for bulk/"closable tickets" requests.
- `generate_report`: Use this to generate a SOAP note report for a closed ticket and send it to the admin.
- `list_tickets`: Lists all tickets assigned to the doctor.

CRITICAL INSTRUCTIONS:
1. When the doctor asks to find closable tickets, or to close all closable/still-open tickets, you MUST call `analyze_closable_tickets` and nothing else — do not call `close_ticket` yourself in this flow. The tool will pause for the doctor's explicit selection via the approval UI and only close what the doctor selects; simply relay its final result to the doctor.
2. Never call `close_ticket` for tickets you only know about because `analyze_closable_tickets` listed them — that tool already handles closing the doctor's selected subset on its own.
3. If no tools are needed, answer the doctor directly.
4. Only answer clinical, healthcare, ticket-management, or report-generation questions. For every other request, respond only: "I can only help with medical care, assigned tickets, and medical reports."
"""
    
    has_system = any(isinstance(m, SystemMessage) for m in messages)
    msgs_to_run = messages if has_system else [SystemMessage(content=system)] + messages
    
    response = await llm_with_tools.ainvoke(msgs_to_run, config)
    return {"messages": [response]}

def route_after_doctor_agent(state: DoctorAgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "doctor_tools_node"
            
    return END

def create_doctor_agent_graph(checkpointer=None):
    """
    Compiles the doctor's agent graph.
    """
    workflow = StateGraph(DoctorAgentState)
    
    workflow.add_node("doctor_agent", doctor_agent_node)
    workflow.add_node("doctor_tools_node", ToolNode(doctor_tools))
    
    workflow.set_entry_point("doctor_agent")
    
    workflow.add_conditional_edges(
        "doctor_agent",
        route_after_doctor_agent,
        {
            "doctor_tools_node": "doctor_tools_node",
            END: END
        }
    )
    
    workflow.add_edge("doctor_tools_node", "doctor_agent")
    
    return workflow.compile(checkpointer=checkpointer)
