from fastapi import APIRouter, Body, HTTPException, status, Request, Depends
from app.dependencies import get_current_user
from app.utils.ai_utils import generate_embedding, generate_medical_response
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.models import Report
from fastapi.responses import StreamingResponse
from langgraph.types import Command
import json

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/query")
async def chat_query(request: Request, payload: dict = Body(...), user = Depends(get_current_user)):
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default-thread")
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query is required"
        )
    
    user_id = str(user.id) if user and hasattr(user, "id") else None
    user_role = user.role if user and hasattr(user, "role") else None
    print(f"DEBUG CHATBOT: user={user}, user_role={user_role}")
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "user_role": user_role
        }
    }
    

    db = request.app.state.sync_client['langgraph_state']
    db.user_threads.update_one(
        {"thread_id": thread_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )
    
    agent_executor = request.app.state.doctor_agent if user_role == "doctor" else request.app.state.agent
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
                
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Streaming Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.post("/approve")
async def chat_approve(request: Request, payload: dict = Body(...), user = Depends(get_current_user)):
    thread_id = payload.get("thread_id", "default-thread")
    action = payload.get("action") 
    
    if not thread_id or not action:
        raise HTTPException(status_code=400, detail="thread_id and action are required")
        
    user_id = str(user.id) if user and hasattr(user, "id") else None
    user_role = user.role if user and hasattr(user, "role") else None
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "user_role": user_role
        }
    }
    
    db = request.app.state.sync_client['langgraph_state']
    db.user_threads.update_one(
        {"thread_id": thread_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )
    
    agent_executor = request.app.state.doctor_agent if user_role == "doctor" else request.app.state.agent
    
    # 1. Fetch current state to find the task ID to resume
    state = await agent_executor.aget_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="No pending action/interrupt found for this session.")
        
    # Extract the task ID to resume
    task_id = None
    for t in getattr(state, "tasks", []):
        if getattr(t, "interrupts", []):
            task_id = t.id
            break
            
    if not task_id:
        raise HTTPException(status_code=400, detail="Could not identify the task to resume.")
        
    # 2. Prepare the resume value
    resume_payload = {"approved": True} if action == "approve" else {"approved": False}
    command = Command(resume=resume_payload)
    
    # 3. Resume the graph and stream the responses
    async def stream_generator():
        try:
            async for event in agent_executor.astream_events(command, config, version="v2"):
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
                            
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Resume Streaming Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@router.get("/threads")
async def list_chat_threads(request: Request, user = Depends(get_current_user)):
    """
    Lists all unique thread IDs from the checkpointer database for the current user.
    """
    try:
        user_id = str(user.id) if user and hasattr(user, "id") else None
        if not user_id:
            return {"threads": []}
            
        db = request.app.state.sync_client['langgraph_state']
        user_threads = db.user_threads.find({"user_id": user_id}).sort("_id", -1)
        
        threads = [t["thread_id"] for t in user_threads]
        return {"threads": threads}
    except Exception as e:
        print(f"Error listing threads: {e}")
        return {"threads": []}

@router.get("/history/{thread_id}")
async def get_chat_history(request: Request, thread_id: str, user = Depends(get_current_user)):
    """
    Retrieves the conversation history for a given thread ID.
    """
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
        if state.next:
            tasks = getattr(state, "tasks", [])
            for t in tasks:
                interrupts = getattr(t, "interrupts", [])
                for intr in interrupts:
                    val = intr.value
                    if isinstance(val, dict) and val.get("action") == "approve_ticket":
                        pending_interrupt = val
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
                    
                    if is_pending:
                        history.append({
                            "role": "assistant",
                            "content": "",
                            "requiresApproval": True,
                            "ticketDetails": pending_interrupt
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
async def delete_chat_thread(request: Request, thread_id: str):
    """
    Permanently deletes a chat thread and all its checkpoints from the database.
    """
    saver = request.app.state.saver
    try:
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
        
        res1 = db["checkpoints"].delete_many({"thread_id": thread_id})
        res2 = db["checkpoint_writes"].delete_many({"thread_id": thread_id})
        res3 = db["user_threads"].delete_many({"thread_id": thread_id})
        
        print(f"Deleted {res1.deleted_count} checkpoints, {res2.deleted_count} writes, and {res3.deleted_count} user threads.")
        
        return {"status": "success", "message": f"Thread {thread_id} deleted successfully."}
    except Exception as e:
        print(f"Error deleting thread: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))