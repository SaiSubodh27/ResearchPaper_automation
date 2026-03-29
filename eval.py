import asyncio
import json
import logging
from router import route_request

# Temporarily silence Litellm verbose logs for clean testing output
logging.getLogger("litellm").setLevel(logging.CRITICAL)

# TIER EXPECTATION LIST (Total: 30)
TEST_PROMPTS = [
    # PATH 1 Expected (SIMPLE - Short / Rules)
    ("What is an API?", 1),
    ("What is pip?", 1),
    ("What year was Python created?", 1),
    ("Write a hello world in Python", 1),
    ("What is JSON?", 1),
    ("What does print() do?", 1),
    ("What is localhost?", 1),
    ("List 3 programming languages", 1),
    ("What is a variable?", 1),
    ("What is Git?", 1),
    
    # PATH 2 Expected (MEDIUM - Embeddings / Non-Complex Keywords)
    ("Explain how async/await works in Python", 2),
    ("What are the differences between list and tuple?", 2),
    ("How does LiteLLM proxy work?", 2),
    ("Explain REST vs GraphQL", 2),
    ("How does SQLite differ from PostgreSQL?", 2),
    ("What is a context window in LLMs?", 2),
    ("Explain Docker containers vs virtual machines", 2),
    ("How does JWT authentication work?", 2),
    ("What is rate limiting and how is it implemented?", 2),
    ("Explain the difference between threading and multiprocessing in Python", 2),
    
    # PATH 3 Expected (COMPLEX - Hardcoded Rules / High Complexity)
    ("Debug this: my FastAPI endpoint returns 422 on valid POST data", 3),
    ("Design a microservices architecture for a real-time chat app", 3),
    ("Why does my Python script leak memory processing large CSV files?", 3),
    ("Refactor this code to be SOLID-compliant", 3),
    ("Compare PostgreSQL vs MongoDB for user session storage with trade-offs", 3),
    ("What security vulnerabilities exist in this JWT implementation?", 3),
    ("Optimize a SQL query taking 8 seconds on 10M rows", 3),
    ("Design a retry strategy with exponential backoff for API failures", 3),
    ("Why does my RouteLLM classifier give inconsistent routing results?", 3),
    ("Build a production-ready rate limiter using Redis and Python", 3)
]

async def run_evaluation():
    session_id = "eval-session-baseline"
    results = []
    
    metrics = {
        "correct_paths": 0,
        "path1_count": 0,
        "path2_count": 0,
        "path3_count": 0,
        "total_cost_usd": 0.0,
        "total_tokens_used": 0,
        "fallbacks_triggered": 0,
        "path3_planner_improvements": []
    }
    
    print("="*60)
    print("STARTING SYSTEM EVALUATION PROTOCOL (30 Queries)")
    print("="*60)
    
    for idx, (prompt, expected_path) in enumerate(TEST_PROMPTS):
        print(f"\n[{idx+1}/30] Evaluating: \"{prompt[:50]}...\"")
        print(f"       Expected Path: {expected_path}")
        
        try:
            # Add a small delay so we don't completely blitz the rate limits on APIs
            await asyncio.sleep(1)
            
            res = await route_request(prompt, session_id=session_id)
            
            # Record base metrics
            actual_path = res["path_used"]
            metrics[f"path{actual_path}_count"] += 1
            metrics["total_cost_usd"] += res["total_cost_usd"]
            metrics["total_tokens_used"] += res["tokens_used"]
            
            if res["fallback_triggered"]:
                metrics["fallbacks_triggered"] += 1
            
            is_correct = (actual_path == expected_path)
            if is_correct:
                metrics["correct_paths"] += 1
            
            # Basic pseudo-evaluation of Path 3 performance
            plan_used = "YES" if res["planner_used"] else "NO"
            print(f"       Actual Path: {actual_path} | Match: {'PASS' if is_correct else 'FAIL'}")
            print(f"       Cost: ${res['total_cost_usd']:.6f} | Tokens: {res['tokens_used']} | Fallback: {res['fallback_triggered']}")
            print(f"       Tier Reason: {res['routing_reason']}")
            if actual_path == 3:
                print(f"       Planner Triggered: {plan_used} | Model: {res['model_used']}")
            
            results.append({
                "prompt": prompt,
                "expected_path": expected_path,
                "actual_path": actual_path,
                "match": is_correct,
                "reason": res["routing_reason"],
                "cost": res["total_cost_usd"],
                "fallback": res["fallback_triggered"]
            })
            
        except Exception as e:
            print(f"       [ERROR] Request failed entirely: {e}")
            metrics["fallbacks_triggered"] += 1
    
    # Calculate comparative savings
    accuracy = (metrics["correct_paths"] / len(TEST_PROMPTS)) * 100
    
    theoretical_cost_per_token = (0.003 + 0.015) / 2000.0  
    all_cloud_cost = metrics["total_tokens_used"] * theoretical_cost_per_token
    savings = all_cloud_cost - metrics["total_cost_usd"]
    savings_pct = (savings / all_cloud_cost * 100) if all_cloud_cost > 0 else 0
    
    print("\n" + "="*60)
    print("EVALUATION REPORT")
    print("="*60)
    print(f"Routing Accuracy:     {accuracy:.1f}% ({metrics['correct_paths']}/{len(TEST_PROMPTS)} matched expectation)")
    print(f"Total Tokens Used:    {metrics['total_tokens_used']}")
    print(f"Actual System Cost:   ${metrics['total_cost_usd']:.4f}")
    print(f"All-Claude-Sonnet Est:${all_cloud_cost:.4f}")
    print(f"Gross Savings:        ${savings:.4f} ({savings_pct:.1f}%)")
    print(f"Fallback Events:      {metrics['fallbacks_triggered']}")
    print(f"Path Breakdown:       1: {metrics['path1_count']} | 2: {metrics['path2_count']} | 3: {metrics['path3_count']}")
    
    # Save off results
    with open("eval_results.json", "w") as f:
        json.dump({
            "metrics": metrics,
            "accuracy": accuracy,
            "all_cloud_cost": all_cloud_cost,
            "savings": savings,
            "savings_pct": savings_pct,
            "logs": results
        }, f, indent=4)
        
    print("\nResults archived to eval_results.json")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
