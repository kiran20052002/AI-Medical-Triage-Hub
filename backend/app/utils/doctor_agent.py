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
    
    system = """You are a specialized medical AI assistant for doctors.
You have access to the following tools:
- `analyze_closable_tickets`: Use this to scan the doctor's open tickets and identify which ones can be closed based on chat history. Use this when the doctor asks to find tickets that can be closed, or when they ask to close ALL closable tickets.
- `close_ticket`: Use this to close a specific ticket ID.
- `generate_report`: Use this to generate a SOAP note report for a closed ticket and send it to the admin.
- `list_tickets`: Lists all tickets assigned to the doctor.

CRITICAL INSTRUCTIONS:
1. When the doctor asks to "close all closable tickets", you MUST first call `analyze_closable_tickets` to get the list of recommended tickets.
2. After receiving the list, you MUST execute `close_ticket` and `generate_report` for EACH ticket in the list. You can make multiple tool calls in a single turn.
3. If no tools are needed, answer the doctor directly.
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
