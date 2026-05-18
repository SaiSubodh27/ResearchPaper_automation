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
        # Fix: Extract only the last user message from context for grounding
        last_user_content = next(
            (m["content"] for m in reversed(context) if m["role"] == "user"), ""
        )

        reasoning_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(plan.get("reasoning_chain", [])))
        constraints_str = "\n".join(f"- {c}" for c in plan.get("constraints", []))
        failures_str = "\n".join(f"- {f}" for f in plan.get("failure_modes", []))
        
        system_directive = f"""You are a precise code/answer generator.

TASK GOAL: {plan.get('goal', 'Complete the task')}

EXECUTION STEPS (follow exactly, in order):
{reasoning_str}

OUTPUT FORMAT: {plan.get('expected_output_format', 'N/A')}

HARD CONSTRAINTS:
{constraints_str}

KNOWN FAILURE MODES TO AVOID:
{failures_str}

Prior context summary: {last_user_content[:200]}"""
        
        # We replace the raw context entirely with just the system directive and current message
        messages = [
            {"role": "system", "content": system_directive},
            {"role": "user", "content": message}
        ]
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
