import asyncio
import os
from embedder import complexity_embedding, similarity_score
from classifier import classify
from cost_estimator import count_tokens, estimate_cost, estimate_path3_cost, track_session_cost
from memory import add_message, get_context, should_compress, compress_session

async def mock_local_call(prompt: str) -> str:
    """Mock local LLM call for testing memory compression."""
    return "MOCK SUMMARY: The user asked about several topics including embeddings, Python, and costs."

async def run_tests():
    print("=== TESTING MODULE 1: embedder.py ===")
    emb1 = complexity_embedding("hello world")
    emb2 = complexity_embedding("hi there")
    score = similarity_score("hello world", "hi there")
    print(f"Embedding shape: {emb1.shape}")
    print(f"Similarity ('hello world' vs 'hi there'): {score:.4f}\n")

    print("=== TESTING MODULE 2: classifier.py ===")
    prompts = [
        "What is pip?",  # Rule -> SIMPLE
        "List 3 programming languages", # Rule -> SIMPLE
        "How do I use async and await in Python?", # Embedding -> MEDIUM
        "Design a microservices architecture for a real-time chat app", # Rule Keyword -> COMPLEX
    ]
    for p in prompts:
        res = classify(p)
        print(f"Prompt: '{p}'")
        print(f"  Tier: {res['tier']} | Path: {res['path']} | Reason: {res['reason']}")
    print()

    print("=== TESTING MODULE 3: cost_estimator.py ===")
    mock_prompt = "Design a microservices architecture for a real-time chat app"
    tokens = count_tokens(mock_prompt)
    print(f"Tokens in prompt: {tokens}")
    
    path1_cost = estimate_cost(mock_prompt, "mistral:7b")
    print(f"Path 1 (Local) Est: ${path1_cost['estimated_cost_usd']:.6f} for {path1_cost['estimated_output_tokens']} out tokens")
    
    path3_cost = estimate_path3_cost(mock_prompt)
    print(f"Path 3 (Plan+Exec) Est: ${path3_cost['total_cost_usd']:.6f} total (Planner: ${path3_cost['planner_cost_usd']:.6f}, Executor: ${path3_cost['executor_cost_usd']:.6f})")
    
    # Test tracking to local DB
    await track_session_cost("test-session-001", "claude-sonnet-4-5", 3, 500, 0.0075)
    print("Tracked cost for test-session-001 successfully.\n")

    print("=== TESTING MODULE 4: memory.py ===")
    session_id = "test-session-002"
    print(f"Adding 10 messages to session {session_id} to trigger compression...")
    for i in range(10):
        await add_message(session_id, "user", f"Message {i+1}")
        await add_message(session_id, "assistant", f"Reply {i+1}")
        
    context = await get_context(session_id)
    # Context should be up to MAX_WINDOW (5 from .env)
    print(f"Context length before compression: {len(context)}")
    
    compress_flag = await should_compress(session_id)
    print(f"Should compress? {compress_flag} (Threshold is COMPRESSION_TRIGGER=10)")
    
    if compress_flag:
        summary = await compress_session(session_id, mock_local_call)
        print(f"Compression complete. Summary: {summary}")
        
        # Test anti-drift
        compress_flag_again = await should_compress(session_id)
        print(f"Should compress again? {compress_flag_again}")
        
        context_after = await get_context(session_id)
        print(f"Context items after compression: {len(context_after)}")
        print(f"First item in context: {context_after[0]['role']} - {context_after[0]['content']}")

if __name__ == "__main__":
    # Ensure our environment is set up for testing
    os.environ["COMPRESSION_TRIGGER"] = "10"
    os.environ["MAX_WINDOW"] = "5"
    asyncio.run(run_tests())
