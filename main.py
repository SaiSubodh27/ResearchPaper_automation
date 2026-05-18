import os
import time
import logging
import aiosqlite
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from litellm import acompletion
from router import route_request, LOCAL_MODEL, OLLAMA_BASE_URL
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "sessions.db")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm Ollama on startup to decrease latency
    try:
        logger.info(f"Pre-warming local model: {LOCAL_MODEL}")
        await acompletion(
            model=LOCAL_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            api_base=OLLAMA_BASE_URL,
            max_tokens=5
        )
        logger.info("Local model pre-warmed successfully.")
    except Exception as e:
        logger.warning(f"Could not pre-warm local model: {e}")
    yield

app = FastAPI(title="Planner-Executor Routing System", 
              description="Locally intelligent routing mechanism splitting workload between planners and executors to optimize constraints and ROI.",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

# --- OpenAI Proxy Schema ---
class OpenAIMessage(BaseModel):
    role: str
    content: str

class OpenAIChatRequest(BaseModel):
    model: str = "router-default"
    messages: List[OpenAIMessage]
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

@app.post("/v1/chat/completions")
async def openai_compatible_chat(request: Request, body: OpenAIChatRequest):
    """
    OpenAI-compatible endpoint. Allows ANY LLM tool (Cursor, Cline, Continue)
    to point to http://localhost:8000/v1 and instantly get the power of the router.
    """
    try:
        # Extract the last user message
        if not body.messages:
            raise HTTPException(status_code=400, detail="No messages provided.")
            
        last_message = body.messages[-1].content
        
        # Extract session ID from headers or body
        session_id = request.headers.get("X-Session-ID", "default-proxy-session")
        if session_id == "default-proxy-session":
            # Generate a random session ID if none provided to avoid bleeding context
            import uuid
            session_id = str(uuid.uuid4())
        
        # Internally map through our router (Planner + Executor + Cost saving)
        result = await route_request(last_message, session_id)
        
        # Construct OpenAI-format response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": result.get("model_used", body.model),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.get("response", "")
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0, # Could be calculated from result
                "completion_tokens": result.get("tokens_used", 0),
                "total_tokens": result.get("tokens_used", 0)
            },
            "routing_metadata": {
                "path_used": result.get("path_used"),
                "tier": result.get("routing_tier"),
                "cost_usd": result.get("total_cost_usd")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Main ingestion endpoint for user queries.
    Passes message to orchestration router.
    """
    try:
        response = await route_request(req.message, req.session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/stats")
async def session_stats(session_id: str):
    """
    Computes and returns the ROI savings and usage statistics for an entire session.
    Calculates exact "would have cost" vs "what it actually cost."
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT path_used, cost_usd, tokens FROM costs WHERE session_id = ?', (session_id,)) as cursor:
                rows = await cursor.fetchall()
                
        if not rows:
            return {"detail": "No stats recorded for session"}
            
        total_cost = sum([r[1] for r in rows])
        total_tokens = sum([r[2] for r in rows])
        path1 = len([r for r in rows if r[0] == 1])
        path2 = len([r for r in rows if r[0] == 2])
        path3 = len([r for r in rows if r[0] == 3])
        
        # Calculate theoretical maximum cost if all queries went directly to Claude Sonnet (0.003/1k input, 0.015/1k output)
        # Using a conservative 1:1 input/output token ratio for standard projection
        theoretical_cost_per_token = (0.003 + 0.015) / 2000.0  
        cost_if_all_claude_sonnet = total_tokens * theoretical_cost_per_token
        
        savings_usd = cost_if_all_claude_sonnet - total_cost
        savings_percent = (savings_usd / cost_if_all_claude_sonnet * 100) if cost_if_all_claude_sonnet > 0 else 0
        
        return {
            "total_cost_usd": round(total_cost, 6),
            "path1_calls": path1,
            "path2_calls": path2,
            "path3_calls": path3,
            "cost_if_all_claude_sonnet": round(cost_if_all_claude_sonnet, 6),
            "savings_usd": round(savings_usd, 6),
            "savings_percent": round(savings_percent, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}/history")
async def session_history(session_id: str):
    """
    Fetches the raw recorded memory state (sliding window + frozen compression flag).
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 20', (session_id,)) as cursor:
                rows = await cursor.fetchall()
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Diagnostic system footprint."""
    return {"status": "operational", "sqlite": True}

@app.delete("/session/{session_id}")
async def wipe_session(session_id: str):
    """Clears short and long term memory for given session identifier."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            await db.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            await db.execute('DELETE FROM costs WHERE session_id = ?', (session_id,))
            await db.commit()
        return {"status": "purged", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
