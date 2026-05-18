import os
import re
import logging
from litellm import acompletion
from typing import Dict, Any, List
from cost_estimator import count_tokens, PRICING

logger = logging.getLogger(__name__)

PLANNER_MODEL = os.getenv("PLANNER_MODEL", "gemini/gemini-2.5-flash")

PLANNER_SYSTEM_PROMPT = """Output ONLY this JSON, nothing else:
{
  "goal": "one sentence",
  "reasoning_chain": [
    "why step 1 is correct and what it achieves",
    "why step 2 follows from step 1",
    "why step 3 is the right ending"
  ],
  "constraints": ["must avoid X", "output must be Y format"],
  "failure_modes": ["common mistake 1", "common mistake 2"],
  "expected_output_format": "describe exact output shape"
}"""

def _parse_plan(content: str) -> Dict[str, Any]:
    """
    Parses the raw JSON output from the planner into a structured dictionary.
    """
    import json
    
    # Strip markdown formatting like ```json or ``` if the model wraps it
    content = content.strip()
    if content.startswith("```json"): content = content[7:]
    elif content.startswith("```"): content = content[3:]
    if content.endswith("```"): content = content[:-3]
    content = content.strip()

    try:
        plan = json.loads(content)
        plan["raw"] = content
        return plan
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing plan JSON: {e} - Content: {content}")
        return {
            "goal": "Execute the task as requested",
            "reasoning_chain": ["Provide standard response based on query"],
            "constraints": [],
            "failure_modes": [],
            "expected_output_format": "Standard text format",
            "raw": content
        }

async def plan(message: str, context: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Given a complex user query, asks a highly-capable model to generate an execution plan.
    
    WHAT IT DOES:
    Sends the user message and session context to the PLANNER_MODEL (Claude Sonnet)
    with a strict system prompt limiting output to structural reasoning without code 
    synthesis. Captures the generated tokens and projects costs using the PRICING table.
    
    WHY IT DOES IT:
    This isolates the 'expensive brain process' of task deduction from the 'expensive token 
    output' of code generation. Creating a plan takes ~150 fast tokens but sets a rigid, 
    highly accurate framework for the cheaper downstream model to follow blindly.
    """
    messages = [{"role": "system", "content": PLANNER_SYSTEM_PROMPT}]
    messages.extend(context)
    messages.append({"role": "user", "content": message})
    
    try:
        response = await acompletion(
            model=PLANNER_MODEL,
            messages=messages,
            max_tokens=500, # Increased budget for valid structured reasoning
            temperature=0.2, # Lower temperature for stable formatting
            response_format={ "type": "json_object" } # Forces valid JSON output natively
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        rates = PRICING.get(PLANNER_MODEL, {"input": 0.0, "output": 0.0})
        input_cost = (response.usage.prompt_tokens / 1000.0) * rates["input"]
        output_cost = (response.usage.completion_tokens / 1000.0) * rates["output"]
        cost_usd = input_cost + output_cost
        
        parsed_plan = _parse_plan(content)
        parsed_plan["planner_tokens_used"] = tokens_used
        parsed_plan["planner_cost_usd"] = cost_usd
        
        return parsed_plan
        
    except Exception as e:
        logger.error(f"Planner API Failed: {e}")
        raise e
