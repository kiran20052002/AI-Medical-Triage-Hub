from fastapi import APIRouter, Body, HTTPException, status, Request, Depends
from app.dependencies import require_user
from app.utils.ai_utils import generate_embedding, generate_medical_response
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.models import Report

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/query")
async def chat_query(request: Request, payload: dict = Body(...)):
    agent_executor = request.app.state.agent
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default-thread")
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query is required"
        )
    
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {"messages": [HumanMessage(content=query)]}

    from fastapi.responses import StreamingResponse
    import json

    async def stream_generator():
        try:
            async for event in agent_executor.astream_events(input_data, config, version="v2"):
                kind = event.get("event")
                
                if kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {}).content
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
                
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"Streaming Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@router.get("/threads")
async def list_chat_threads(request: Request):
    """
    Lists all unique thread IDs from the checkpointer database.
    """
    saver = request.app.state.saver
    try:
        threads = []
        print("--- LISTING THREADS ---")
        async for checkpoint in saver.alist(config=None):
            print(f"Checkpoint found: {checkpoint.config}")
            conf = checkpoint.config.get("configurable", {})
            thread_id = conf.get("thread_id")
            if thread_id and thread_id not in threads:
                threads.append(thread_id)
        print(f"Threads found: {threads}")
        return {"threads": threads}
    except Exception as e:
        print(f"Error listing threads: {e}")
        return {"threads": []}

@router.get("/history/{thread_id}")
async def get_chat_history(request: Request, thread_id: str):
    """
    Retrieves the conversation history for a given thread ID.
    """
    agent_executor = request.app.state.agent
    print(f"--- FETCHING HISTORY FOR THREAD: {thread_id} ---")
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await agent_executor.aget_state(config)
        print(f"State retrieved: {True if state else False}")
        
        if not state or not state.values:
            return {"history": [], "thread_id": thread_id}
            
        messages = state.values.get("messages", [])
        history = []
        for msg in messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            history.append({"role": role, "content": msg.content})
            
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
            raise Exception("Could not find MongoDB client in weaver")
            
        db = client[db_name]
        
        res1 = db["checkpoints"].delete_many({"thread_id": thread_id})
        res2 = db["writes"].delete_many({"thread_id": thread_id})
        
        print(f"Deleted {res1.deleted_count} checkpoints and {res2.deleted_count} writes.")
        
        return {"status": "success", "message": f"Thread {thread_id} deleted successfully."}
    except Exception as e:
        print(f"Error deleting thread: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))