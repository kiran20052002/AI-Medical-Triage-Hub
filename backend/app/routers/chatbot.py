from fastapi import APIRouter, Body, HTTPException, status, Request, Depends
from app.dependencies import require_user
from app.utils.ai_utils import generate_embedding, generate_medical_response, is_in_scope_chat_query
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.models import Report
from fastapi.responses import StreamingResponse
from langgraph.types import Command
import json
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


def user_threads_collection(request: Request):
    return request.app.state.sync_client["langgraph_state"].user_threads


def user_owns_thread(request: Request, thread_id: str, user_id: str) -> bool:
    return bool(
        user_threads_collection(request).find_one({"thread_id": thread_id, "user_id": user_id})
    )


def create_thread(request: Request, user_id: str) -> str:
    thread_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    user_threads_collection(request).insert_one(
        {
            "thread_id": thread_id,
            "user_id": user_id,
            "created_at": now,
            "last_active_at": now,
        }
    )
    return thread_id


def touch_thread(request: Request, thread_id: str, user_id: str) -> None:
    result = user_threads_collection(request).update_one(
        {"thread_id": thread_id, "user_id": user_id},
        {"$set": {"last_active_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")


def require_owned_thread(request: Request, thread_id: str, user_id: str) -> None:
    if not user_owns_thread(request, thread_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")


@router.post("/threads")
async def create_chat_thread(request: Request, user=Depends(require_user)):
    user_id = str(user.id)
    thread_id = create_thread(request, user_id)
    return {"thread_id": thread_id}


@router.post("/query")
async def chat_query(request: Request, payload: dict = Body(...), user = Depends(require_user)):
    query = payload.get("query")
    thread_id = payload.get("thread_id")

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query is required",
        )
    if not thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="thread_id is required",
        )

    user_id = str(user.id) if user and hasattr(user, "id") else None
    user_role = user.role if user and hasattr(user, "role") else None
    print(f"DEBUG CHATBOT: user={user}, user_role={user_role}")

    require_owned_thread(request, thread_id, user_id)
    touch_thread(request, thread_id, user_id)

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "user_role": user_role
        }
    }

    agent_executor = request.app.state.doctor_agent if user_role == "doctor" else request.app.state.agent

    if not await is_in_scope_chat_query(query, user_role):
        response = "I can only help with medical, healthcare, and medical support-ticket questions. Please ask a health-related question."
        checkpoint_node = "doctor_agent" if user_role == "doctor" else "agent"
        await agent_executor.aupdate_state(
            config,
            {"messages": [HumanMessage(content=query), AIMessage(content=response)]},
            as_node=checkpoint_node,
        )

        async def out_of_scope_stream():
            yield f"data: {json.dumps({'content': response})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(out_of_scope_stream(), media_type="text/event-stream")

    input_data = {"messages": [HumanMessage(content=query)]}

    async def stream_generator():
        try:
            async for event in agent_executor.astream_events(input_data, config, version="v2"):
                kind = event.get("event")
                
                if kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {}).content
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
            
            # Check if graph has hit an interrupt
            state = await agent_executor.aget_state(config)
            if state.next:
                tasks = getattr(state, "tasks", [])
                for t in tasks:
                    interrupts = getattr(t, "interrupts", [])
                    for intr in interrupts:
                        val = intr.value
                        if isinstance(val, dict) and val.get("action") == "approve_ticket":
                            yield f"data: {json.dumps({'status': 'requires_approval', 'ticket_details': val})}\n\n"
                        elif isinstance(val, dict) and val.get("action") == "approve_ticket_closures":
                            yield f"data: {json.dumps({'status': 'requires_closure_approval', 'closure_details': val})}\n\n"
                        elif isinstance(val, dict) and val.get("action") == "approve_report_generation":
                            yield f"data: {json.dumps({'status': 'requires_report_approval', 'report_details': val})}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Streaming Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/approve")
async def chat_approve(request: Request, payload: dict = Body(...), user = Depends(require_user)):
    thread_id = payload.get("thread_id")
    action = payload.get("action")
    selected_ids = payload.get("selected_ids")

    if not thread_id or not action:
        raise HTTPException(status_code=400, detail="thread_id and action are required")

    user_id = str(user.id) if user and hasattr(user, "id") else None
    user_role = user.role if user and hasattr(user, "role") else None

    require_owned_thread(request, thread_id, user_id)
    touch_thread(request, thread_id, user_id)

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "user_role": user_role
        }
    }
    
    agent_executor = request.app.state.doctor_agent if user_role == "doctor" else request.app.state.agent
    
    state = await agent_executor.aget_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="No pending action/interrupt found for this session.")
        
    task_id = None
    pending_action = None
    for t in getattr(state, "tasks", []):
        interrupts = getattr(t, "interrupts", [])
        if interrupts:
            task_id = t.id
            val = interrupts[0].value
            if isinstance(val, dict):
                pending_action = val.get("action")
            break

    if not task_id:
        raise HTTPException(status_code=400, detail="Could not identify the task to resume.")

    approved = action == "approve"
    if pending_action in ("approve_ticket_closures", "approve_report_generation"):
        resume_payload = {"approved": approved, "selected_ids": selected_ids or []}
    else:
        resume_payload = {"approved": approved}
    command = Command(resume=resume_payload)
    
    async def stream_generator():
        try:
            async for event in agent_executor.astream_events(command, config, version="v2"):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {}).content
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
            
            state = await agent_executor.aget_state(config)
            if state.next:
                tasks = getattr(state, "tasks", [])
                for t in tasks:
                    interrupts = getattr(t, "interrupts", [])
                    for intr in interrupts:
                        val = intr.value
                        if isinstance(val, dict) and val.get("action") == "approve_ticket":
                            yield f"data: {json.dumps({'status': 'requires_approval', 'ticket_details': val})}\n\n"
                        elif isinstance(val, dict) and val.get("action") == "approve_ticket_closures":
                            yield f"data: {json.dumps({'status': 'requires_closure_approval', 'closure_details': val})}\n\n"
                        elif isinstance(val, dict) and val.get("action") == "approve_report_generation":
                            yield f"data: {json.dumps({'status': 'requires_report_approval', 'report_details': val})}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Resume Streaming Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.get("/threads")
async def list_chat_threads(request: Request, user = Depends(require_user)):
    """
    Lists all unique thread IDs from the checkpointer database for the current user.
    """
    try:
        user_id = str(user.id) if user and hasattr(user, "id") else None
        if not user_id:
            return {"threads": []}
            
        db = request.app.state.sync_client['langgraph_state']
        user_threads = db.user_threads.find({"user_id": user_id}).sort("last_active_at", -1)
        
        threads = [thread["thread_id"] for thread in user_threads]
        return {"threads": threads}
    except Exception as e:
        print(f"Error listing threads: {e}")
        return {"threads": []}

@router.get("/history/{thread_id}")
async def get_chat_history(request: Request, thread_id: str, user = Depends(require_user)):
    """
    Retrieves the conversation history for a given thread ID.
    """
    user_id = str(user.id)
    require_owned_thread(request, thread_id, user_id)

    user_role = user.role if user and hasattr(user, "role") else None
    agent_executor = request.app.state.doctor_agent if user_role == "doctor" else request.app.state.agent
    print(f"--- FETCHING HISTORY FOR THREAD: {thread_id} ---")
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await agent_executor.aget_state(config)
        print(f"State retrieved: {True if state else False}")
        
        if not state or not state.values:
            return {"history": [], "thread_id": thread_id}
            
        messages = state.values.get("messages", [])
        
        pending_interrupt = None
        pending_closure_interrupt = None
        pending_report_interrupt = None
        if state.next:
            tasks = getattr(state, "tasks", [])
            for t in tasks:
                interrupts = getattr(t, "interrupts", [])
                for intr in interrupts:
                    val = intr.value
                    if isinstance(val, dict) and val.get("action") == "approve_ticket":
                        pending_interrupt = val
                        break
                    if isinstance(val, dict) and val.get("action") == "approve_ticket_closures":
                        pending_closure_interrupt = val
                        break
                    if isinstance(val, dict) and val.get("action") == "approve_report_generation":
                        pending_report_interrupt = val
                        break
        
        history = []
        for msg in messages:

            if isinstance(msg, SystemMessage):
                continue
            
            if isinstance(msg, ToolMessage):
                continue
                
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
                continue
                
            if isinstance(msg, AIMessage):
                
                if hasattr(msg, "tool_calls") and msg.tool_calls:

                    is_pending = False
                    if pending_interrupt:
                        for tc in msg.tool_calls:
                            if tc.get("name") == "create_ticket":
                                args = tc.get("args", {})
                                if args.get("title") == pending_interrupt.get("title") and args.get("description") == pending_interrupt.get("description"):
                                    is_pending = True
                                    break

                    is_pending_closure = False
                    if pending_closure_interrupt:
                        for tc in msg.tool_calls:
                            if tc.get("name") == "analyze_closable_tickets":
                                is_pending_closure = True
                                break

                    is_pending_report = False
                    if pending_report_interrupt:
                        for tc in msg.tool_calls:
                            if tc.get("name") == "analyze_reportable_tickets":
                                is_pending_report = True
                                break

                    if is_pending:
                        history.append({
                            "role": "assistant",
                            "content": "",
                            "requiresApproval": True,
                            "ticketDetails": pending_interrupt
                        })
                    elif is_pending_closure:
                        history.append({
                            "role": "assistant",
                            "content": "",
                            "requiresClosureApproval": True,
                            "closureDetails": pending_closure_interrupt
                        })
                    elif is_pending_report:
                        history.append({
                            "role": "assistant",
                            "content": "",
                            "requiresReportApproval": True,
                            "reportDetails": pending_report_interrupt
                        })
                else:
                    
                    if msg.content and msg.content.strip():
                        history.append({"role": "assistant", "content": msg.content})
            
        return {
            "history": history,
            "thread_id": thread_id
        }
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/thread/{thread_id}")
async def delete_chat_thread(request: Request, thread_id: str, user = Depends(require_user)):
    """
    Permanently deletes a chat thread and all its checkpoints from the database.
    """
    saver = request.app.state.saver
    try:
        user_id = str(user.id)
        print(f"--- DELETING THREAD: {thread_id} ---")
        import traceback
        
        client = getattr(saver, 'client', None)
        db_name = getattr(saver, 'db_name', 'langgraph_state')
        
        if not client and hasattr(saver, 'db'):
            client = saver.db.client
            db_name = saver.db.name
            
        if not client:
            raise Exception("Could not find MongoDB client in saver")
            
        db = client[db_name]
        require_owned_thread(request, thread_id, user_id)

        res1 = db["checkpoints"].delete_many({"thread_id": thread_id})
        res2 = db["checkpoint_writes"].delete_many({"thread_id": thread_id})
        res3 = db["user_threads"].delete_many({"thread_id": thread_id, "user_id": user_id})
        
        print(f"Deleted {res1.deleted_count} checkpoints, {res2.deleted_count} writes, and {res3.deleted_count} user threads.")
        
        return {"status": "success", "message": f"Thread {thread_id} deleted successfully."}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        print(f"Error deleting thread: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
