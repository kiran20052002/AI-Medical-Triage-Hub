from fastapi import APIRouter, Body, HTTPException, status, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.dependencies import require_user
from app.utils.ai_utils import generate_embedding, generate_medical_response
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.models import Report

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def chatbot_page(request: Request, user = Depends(require_user)):
    """
    Serves the full-page chatbot UI.
    """
    return templates.TemplateResponse("chatbot_full_page.html", {
        "request": request,
        "user": user
    })

@router.post("/query")
async def chat_query(request: Request, payload: dict = Body(...)):
    agent_executor = request.app.state.agent
    query = payload.get("query")
    thread_id = payload.get("thread_id", "default-thread")
    stream = payload.get("stream", False)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Query is required"
        )
    
    config = {"configurable": {"thread_id": thread_id}}
    input_data = {"messages": [HumanMessage(content=query)]}

    if stream:
        from fastapi.responses import StreamingResponse
        import json

        async def stream_generator():
            try:
                # Use astream_events for granular token streaming
                async for event in agent_executor.astream_events(input_data, config, version="v2"):
                    kind = event["event"]
                    # We want tokens from the final generation nodes
                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"Streaming Error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Fallback to sync invoke if not streaming
    try:
        from fastapi.concurrency import run_in_threadpool
        result = await run_in_threadpool(agent_executor.invoke, input_data, config)
        
        # Get the last AI message
        messages = result.get("messages", [])
        final_response = "I'm sorry, I encountered an issue."
        if messages and isinstance(messages[-1], AIMessage):
            final_response = messages[-1].content
        
        return {
            "response": final_response, 
            "thread_id": thread_id
        }
        
    except Exception as e:
        print(f"Agentic Chatbot Error: {e}")
        return {
            "response": "I'm sorry, I am having trouble connecting right now.",
            "thread_id": thread_id
        }

@router.get("/threads")
async def list_chat_threads(request: Request):
    """
    Lists all unique thread IDs from the checkpointer database.
    """
    saver = request.app.state.saver
    try:
        threads = []
        # list() returns an async iterator of CheckpointTuple
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
        from fastapi.concurrency import run_in_threadpool
        config = {"configurable": {"thread_id": thread_id}}
        state = await run_in_threadpool(agent_executor.get_state, config)
        print(f"State retrieved: {True if state else False}")
        
        if not state or not state.values:
            return {"history": [], "thread_id": thread_id}
            
        messages = state.values.get("messages", [])
        # Convert LangChain messages to a serializable format
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