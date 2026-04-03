import os
import logging
from litellm import acompletion
from typing import Dict, Any, List

from memory import get_context, add_message, should_compress, compress_session
from classifier import classify
from cost_estimator import estimate_cost, estimate_path3_cost, track_session_cost, PRICING
from planner import plan
from executor import execute

logger = logging.getLogger(__name__)

LOCAL_MODEL = os.getenv("LOCAL_MODEL", "ollama/mistral:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

async def _compression_call(prompt: str) -> str:
    """Helper wrapper for calling Groq to perform fast, cheap memory compression."""
    try:
        resp = await acompletion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"Compression model call failed: {e}")
        return "Summary failed due to model unavailability."

async def route_request(message: str, session_id: str) -> Dict[str, Any]:
    """
    Master Orchestrator for the entire Planner-Executor routing system.
    
    WHAT IT DOES:
    1. Fetches conversation history.
    2. Runs Layer 1 & 2 Classifications to map intent/complexity to a routing Path.
    3. Projects cost upfront.
    4. Routes execution to Local (Path 1), Executor Cloud (Path 2), or Planner+Executor Cloud (Path 3).
    5. Implements multi-tier failback (Ollama -> Gemini -> Haiku -> Error).
    6. Logs actual token costs into SQLite.
    7. Evaluates state for short-to-long-term Memory Compression.
    
    WHY IT DOES IT:
    To unify multi-model calls into a single endpoint while drastically cutting cloud costs 
    for developers dynamically. It protects system uptime by gracefully tumbling down to 
    cheaper capability APIs if primary services go offline.
    """
    # 1. Memory retrieval
    context = await get_context(session_id)
    
    # 2. Classification
    classification = classify(message)
    tier = classification["tier"]
    target_path = classification["path"]
    routing_reason = classification["reason"]
    
    # Pre-declare response object limits
    fallback_triggered = False
    fallback_reason = None
    final_response = ""
    model_used = ""
    tokens_used = 0
    total_cost_usd = 0.0
    planner_used = False
    planner_cost_usd = 0.0
    executor_cost_usd = 0.0
    
    # Execute branches with Fallback Chain
    try:
        if target_path == 1:
            try:
                # PATH 1 -> LOCAL
                messages = list(context)
                messages.append({"role": "user", "content": message})
                
                resp = await acompletion(
                    model=LOCAL_MODEL,
                    messages=messages,
                    api_base=OLLAMA_BASE_URL
                )
                final_response = resp.choices[0].message.content
                model_used = LOCAL_MODEL
                tokens_used = resp.usage.total_tokens
                # Cost is inherently $0.00 for local models
            except Exception as e:
                # Fallback: Local offline -> Drop to Path 2 (Direct Groq)
                logger.warning(f"Path 1 (Local) failed, cascading to Path 2: {e}")
                fallback_triggered = True
                fallback_reason = f"Local model '{LOCAL_MODEL}' offline. Escalated to direct cloud executor (Groq)."
                target_path = 2
                
        if target_path == 2:
            try:
                # PATH 2 -> MEDIUM CLOUD (Executor Only)
                res = await execute(message, context)
                final_response = res["response"]
                model_used = res["executor_model"]
                tokens_used = res["tokens_used"]
                total_cost_usd = res["cost_usd"]
                executor_cost_usd = res["cost_usd"]
            except Exception as e:
                # Fallback: Groq offline or Rate Limited -> Drop to OpenRouter Free Model
                logger.warning(f"Path 2 (Executor) failed, cascading to OpenRouter Free: {e}")
                fallback_triggered = True
                fallback_reason = f"Executor '{os.getenv('EXECUTOR_MODEL')}' failed (Rate limit/Offline). Cascaded to OpenRouter free fallback."
                fallback_model = os.getenv("FALLBACK_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct:free")
                messages = list(context)
                messages.append({"role": "user", "content": message})
                resp = await acompletion(model=fallback_model, messages=messages)
                final_response = resp.choices[0].message.content
                model_used = fallback_model
                tokens_used = resp.usage.total_tokens
                
                total_cost_usd = 0.0 # OpenRouter Free tier
                
        if target_path == 3:
            try:
                # PATH 3 -> COMPLEX CLOUD (Planner + Executor)
                try:
                    plan_result = await plan(message, context)
                    planner_used = True
                    planner_cost_usd = plan_result["planner_cost_usd"]
                    tokens_used += plan_result["planner_tokens_used"]
                except Exception as eval_e:
                    logger.warning(f"Planner failed, bypassing to Path 2 direct execution: {eval_e}")
                    fallback_triggered = True
                    fallback_reason = f"Planner '{os.getenv('PLANNER_MODEL')}' down. Bypassed to direct executor."
                    plan_result = None

                res = await execute(message, context, plan=plan_result)
                final_response = res["response"]
                model_used = f"Planner + {res['executor_model']}" if planner_used else res["executor_model"]
                tokens_used += res["tokens_used"]
                executor_cost_usd = res["cost_usd"]
                total_cost_usd = planner_cost_usd + executor_cost_usd
            except Exception as e:
                # Fallback: Path 3 full failure -> Drop to OpenRouter Free Model
                logger.warning(f"Path 3 failed entirely, cascading to OpenRouter Free: {e}")
                fallback_triggered = True
                fallback_reason = "Path 3 process failed (Quota/Offline). Cascaded to OpenRouter free fallback."
                fallback_model = os.getenv("FALLBACK_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct:free")
                messages = list(context)
                messages.append({"role": "user", "content": message})
                resp = await acompletion(model=fallback_model, messages=messages)
                final_response = resp.choices[0].message.content
                model_used = fallback_model
                tokens_used = resp.usage.total_tokens
                
                total_cost_usd = 0.0 # OpenRouter Free tier

    except Exception as critical_e:
        logger.error(f"Complete systemic failure across all fallback paths: {critical_e}")
        return {
            "response": f"Internal System Error: All language models are unreachable. ({critical_e})",
            "path_used": target_path,
            "routing_tier": tier,
            "routing_reason": routing_reason,
            "model_used": "NONE",
            "planner_used": False,
            "planner_cost_usd": 0.0,
            "executor_cost_usd": 0.0,
            "total_cost_usd": 0.0,
            "tokens_used": 0,
            "fallback_triggered": True,
            "fallback_reason": "ALL SYSTEMS OFFLINE",
            "session_id": session_id
        }

    # 6. Cost Tracking
    await track_session_cost(session_id, model_used, target_path, tokens_used, total_cost_usd)
    
    # 7. Add messages to local memory context
    await add_message(session_id, "user", message)
    await add_message(session_id, "assistant", final_response)
    
    # 8. Check for sliding window memory compression logic
    if await should_compress(session_id):
        # We spawn compression directly without blocking standard execution time length
        import asyncio
        asyncio.create_task(compress_session(session_id, _compression_call))

    return {
        "response": final_response,
        "path_used": target_path,
        "routing_tier": tier,
        "routing_reason": routing_reason,
        "model_used": model_used,
        "planner_used": planner_used,
        "planner_cost_usd": planner_cost_usd,
        "executor_cost_usd": executor_cost_usd,
        "total_cost_usd": total_cost_usd,
        "tokens_used": tokens_used,
        "fallback_triggered": fallback_triggered,
        "fallback_reason": fallback_reason,
        "session_id": session_id
    }
