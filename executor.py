import os
import logging
from litellm import acompletion
from typing import Dict, Any, List, Optional
from cost_estimator import count_tokens, PRICING

logger = logging.getLogger(__name__)

EXECUTOR_MODEL = os.getenv("EXECUTOR_MODEL", "groq/llama-3.3-70b-versatile")

async def execute(message: str, context: List[Dict[str, str]], plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a user request directly (PATH 2) or by following a structured plan (PATH 3).
    
    WHAT IT DOES:
    If no plan is provided, it passes the context and user message to the EXECUTOR_MODEL natively.
    If a plan is provided, it mutates the prompt to forcefully bound the LLM into answering only
    by following the exact steps provided by the planner. Calculates final tokens and API costs.
    
    WHY IT DOES IT:
    By passing the planning context explicitly via prompt injection, we constrain a mathematically 
    weaker model (Gemini Pro compared to Sonnet) into behaving like a stronger model, while 
    operating at a fraction of the cost per token.
    """
    messages = list(context)
    
    if plan and "reasoning_chain" in plan:
        # PATH 3: Execute via Plan Execution Strategy (Strong Knowledge Distillation)
        reasoning_str = "\n".join(plan.get("reasoning_chain", []))
        constraints_str = "\n".join(plan.get("constraints", []))
        failures_str = "\n".join(plan.get("failure_modes", []))
        
        enhanced_prompt = f"""Task: {message}

You are executing a plan designed by an expert reasoning system. Follow the reasoning chain exactly. Do not deviate.

Reasoning Chain:
{reasoning_str}

Hard Constraints:
{constraints_str}

Your output must match exactly:
{plan.get('expected_output_format', 'N/A')}

These are common mistakes this task has — avoid them:
{failures_str}"""
        
        messages.append({"role": "user", "content": enhanced_prompt})
    else:
        # PATH 2: Direct Execution Strategy (with Max-Output Clamping)
        clamped_prompt = f"{message}\n\n[SYSTEM CONSTRAINT: Output ONLY the requested code or direct answer. Omit all greetings, explanations, pleasantries, and unnecessary markdown wrappers. Be extremely concise.]"
        messages.append({"role": "user", "content": clamped_prompt})
        
    try:
        response = await acompletion(
            model=EXECUTOR_MODEL,
            messages=messages,
            temperature=0.4
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        rates = PRICING.get(EXECUTOR_MODEL, {"input": 0.0, "output": 0.0})
        input_cost = (response.usage.prompt_tokens / 1000.0) * rates["input"]
        output_cost = (response.usage.completion_tokens / 1000.0) * rates["output"]
        cost_usd = input_cost + output_cost
        
        return {
            "response": content,
            "executor_model": EXECUTOR_MODEL,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd
        }
        
    except Exception as e:
        logger.error(f"Executor API Failed: {e}")
        raise e
