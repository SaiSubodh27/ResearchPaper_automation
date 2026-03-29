import os
import json
import logging
import tiktoken
import aiosqlite
from datetime import datetime, timezone
from typing import Dict, Union, List, Any

# Logging setup to prevent silent crashes
logger = logging.getLogger(__name__)

# Pricing Table (Cost per 1,000 tokens in USD)
# FREE TIER ASSUMPTIONS: Tracking risk of hitting rate limits via dummy threshold logic
PRICING = {
    "mistral:7b": {"input": 0.0, "output": 0.0},
    "gemini/gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "groq/llama-3.3-70b-versatile": {"input": 0.0, "output": 0.0},
    "openrouter/meta-llama/llama-3.1-8b-instruct:free": {"input": 0.0, "output": 0.0}
}

DB_PATH = os.getenv("DB_PATH", "sessions.db")

def count_tokens(text: Union[str, List[Dict[str, str]]]) -> int:
    """
    Counts the approximate number of tokens in a text or message list.
    
    WHAT IT DOES:
    Uses tiktoken's 'cl100k_base' encoding to count tokens. If a list of message
    dictionaries is passed (like LiteLLM format), it stringifies them first.
    
    WHY IT DOES IT:
    We need an accurate token count BEFORE making API calls to forecast routing costs.
    This empowers the system with price-awareness, allowing it to evaluate if
    a query is too expensive for a given path.
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        if isinstance(text, list):
            # Very rough approximation for messages format
            text = " ".join([m.get("content", "") for m in text if isinstance(m, dict)])
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {e}")
        # Fallback heuristic: 1 token ≈ 4 characters
        text_str = str(text)
        return len(text_str) // 4

def estimate_cost(messages: Union[str, List[Dict[str, str]]], model: str) -> Dict[str, Union[float, int, bool]]:
    """
    Estimates the cost of an API call for a single model based on input length.
    Now supports free-tier risk detection.
    """
    input_tokens = count_tokens(messages)
    estimated_output_tokens = max(100, int(input_tokens * 0.5)) 
    
    total_tokens = input_tokens + estimated_output_tokens
    
    # 70B Groq models typically cap around 6000 TPM on free tier, Flash 1M TPM.
    # Marking arbitrary danger bounds based on token size.
    quota_risk = False
    if "groq" in model and total_tokens > 4000:
        quota_risk = True
    if "gemini" in model and total_tokens > 20000:
        quota_risk = True
    
    rates = PRICING.get(model, {"input": 0.0, "output": 0.0})
    
    input_cost = (input_tokens / 1000.0) * rates["input"]
    output_cost = (estimated_output_tokens / 1000.0) * rates["output"]
    total_cost = input_cost + output_cost
    
    return {
        "model": model,
        "input_tokens": input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "estimated_cost_usd": total_cost,
        "quota_risk": quota_risk
    }

def estimate_path3_cost(prompt: str) -> Dict[str, Union[float, int, bool]]:
    """
    Estimates the combined cost for a PATH 3 execution (Planner + Executor).
    Modified for free tier quota risk detection.
    """
    input_tokens = count_tokens(prompt)
    
    # 1. Planner Cost
    planner_model = "gemini/gemini-2.5-flash"
    planner_rates = PRICING.get(planner_model, {"input": 0.0, "output": 0.0})
    planner_input_cost = (input_tokens / 1000.0) * planner_rates["input"]
    planner_output_tokens = 150 
    planner_output_cost = (planner_output_tokens / 1000.0) * planner_rates["output"]
    planner_total = planner_input_cost + planner_output_cost
    
    # 2. Executor Cost
    executor_model = "groq/llama-3.3-70b-versatile"
    executor_input_tokens = input_tokens + planner_output_tokens
    executor_input_cost = (executor_input_tokens / 1000.0) * planner_rates["input"]
    
    executor_output_tokens = max(100, int(input_tokens * 0.5))
    executor_output_cost = (executor_output_tokens / 1000.0) * planner_rates["output"]
    executor_total = executor_input_cost + executor_output_cost
    
    total_tokens = input_tokens + planner_output_tokens + executor_output_tokens
    quota_risk = True if total_tokens > 4000 else False
    
    return {
        "planner_cost_usd": planner_total,
        "executor_cost_usd": executor_total,
        "total_cost_usd": planner_total + executor_total,
        "total_estimated_tokens": total_tokens,
        "quota_risk": quota_risk
    }

async def track_session_cost(session_id: str, model: str, path_used: int, tokens: int, cost_usd: float) -> None:
    """
    Asynchronously logs the actual real-world API cost into a local SQLite database.
    
    WHAT IT DOES:
    Creates a 'costs' table if it doesn't exist. Inserts a record containing the 
    session ID, timestamp, model used, routing path, total tokens, and USD cost.
    
    WHY IT DOES IT:
    Provides the data backend for the '/session/{session_id}/stats' endpoint. It is 
    crucial for the product's primary claim: proving that PATH 3 routing is cheaper
    than using Claude for everything. Async IO prevents logging from blocking the API.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS costs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    path_used INTEGER NOT NULL,
                    tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL
                )
            ''')
            
            timestamp = datetime.now(timezone.utc).isoformat()
            await db.execute('''
                INSERT INTO costs (session_id, timestamp, model, path_used, tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, timestamp, model, path_used, tokens, cost_usd))
            
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to track session cost for {session_id}: {e}")
        # Never crash silently, but don't break the main flow for a telemetry failure.
