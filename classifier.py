import os
import tiktoken
import numpy as np
from typing import Dict, Any, Tuple
from embedder import complexity_embedding, similarity_score

# Complex keywords that trigger PATH 3 (COMPLEX)
COMPLEX_KEYWORDS = [
    "debug", "why does", "architecture", "design", "explain the difference",
    "optimize", "refactor", "security", "compare", "trade-off", "reason",
    "best approach", "system design", "root cause", "performance bottleneck",
    "implement from scratch"
]

# Reference prompts for Layer 2 embedding similarity evaluation
REFERENCE_PROMPTS = {
    "SIMPLE": [
        "What is an API?",
        "What is pip?",
        "What year was Python created?",
        "Write a hello world in Python",
        "What is JSON?"
    ],
    "MEDIUM": [
        "Explain how async/await works in Python",
        "What are the differences between list and tuple?",
        "How does LiteLLM proxy work?",
        "Explain REST vs GraphQL",
        "What is a context window in LLMs?"
    ],
    "COMPLEX": [
        "Debug this: my FastAPI endpoint returns 422 on valid POST data",
        "Design a microservices architecture for a real-time chat app",
        "Why does my Python script leak memory processing large CSV files?",
        "Refactor this code to be SOLID-compliant",
        "Optimize a SQL query taking 8 seconds on 10M rows"
    ]
}

# Pre-compute embeddings for reference prompts to save time during classification
REFERENCE_EMBEDDINGS: Dict[str, list[np.ndarray]] = {
    tier: [complexity_embedding(prompt) for prompt in prompts]
    for tier, prompts in REFERENCE_PROMPTS.items()
}

def count_tokens(text: str) -> int:
    """
    Counts the number of tokens in the prompt using tiktoken.
    
    WHAT IT DOES:
    Uses the 'cl100k_base' encoding (standard for recent OpenAI models) to get an
    approximate token count of the input string.
    
    WHY IT DOES IT:
    Token count is a primary heuristic for Layer 1 classification. Very short prompts
    are typically simple factual questions, while very long prompts (e.g., those including
    code snippets or logs) are inherently complex.
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback heuristic if tokenization fails
        return len(text.split())

def _layer_1_rules(prompt: str, token_count: int) -> Tuple[str | None, int | None, str]:
    """
    Applies strict heuristic rules to classify the prompt in O(N) time.
    
    WHAT IT DOES:
    Checks token length and the presence of high-weight complexity keywords to quickly 
    bucket the prompt into SIMPLE or COMPLEX tiers. It leaves ambiguity for MEDIUM.
    
    WHY IT DOES IT:
    Embeddings and similarity comparisons are computationally more expensive than simple string 
    matching. By quickly routing the obvious cases (short text vs explicit design tasks), 
    we reduce latency and save CPU cycles.
    """
    prompt_lower = prompt.lower()
    
    # Check for complex keywords
    has_complex_keyword = any(kw in prompt_lower for kw in COMPLEX_KEYWORDS)
    
    # Rule 1: Short & No complex keywords -> SIMPLE
    if token_count < 50 and not has_complex_keyword:
        return "SIMPLE", 1, "Token count < 50 and no complex keywords detected"
        
    # Rule 2: Long OR Contains complex keywords -> COMPLEX
    if token_count > 200 or has_complex_keyword:
        reason = "Contains complex keywords" if has_complex_keyword else "Token count > 200"
        return "COMPLEX", 3, f"{reason}"
        
    # If it falls between 50-200 tokens and has no obvious complex keywords, it is ambiguous
    return None, None, "Ambiguous length (50-200) with no explicit complex keywords"

def _layer_2_embeddings(prompt: str) -> Tuple[str, int, float, str]:
    """
    Uses vector embeddings to classify the prompt by comparing it to reference prompts.
    
    WHAT IT DOES:
    Generates an embedding for the user prompt and computes the average cosine similarity 
    between it and the predefined sets of SIMPLE, MEDIUM, and COMPLEX reference prompts. 
    The tier with the highest average similarity wins.
    
    WHY IT DOES IT:
    Rule-based routing is brittle. When a prompt doesn't trigger obvious length or keyword 
    rules, its semantic intent determines its complexity. Layer 2 captures this nuance.
    """
    target_emb = complexity_embedding(prompt)
    target_emb = target_emb.reshape(1, -1)
    
    scores = {}
    from sklearn.metrics.pairwise import cosine_similarity
    
    for tier, embeddings in REFERENCE_EMBEDDINGS.items():
        tier_scores = [cosine_similarity(target_emb, ref.reshape(1, -1))[0][0] for ref in embeddings]
        scores[tier] = float(np.mean(tier_scores))
        
    best_tier = max(scores, key=scores.get)
    best_score = scores[best_tier]
    
    path_map = {"SIMPLE": 1, "MEDIUM": 2, "COMPLEX": 3}
    
    return best_tier, path_map[best_tier], best_score, f"Highest cosine similarity ({best_score:.2f}) matches {best_tier} references"

def classify(prompt: str) -> Dict[str, Any]:
    """
    The main classification function that determines the routing path.
    
    WHAT IT DOES:
    Orchestrates the two-layer classification pipeline. It first applies Layer 1 (Rules). 
    If Layer 1 is conclusive, it returns the result immediately. Otherwise, it falls back 
    to Layer 2 (Embedding similarity) to make a final decision.
    
    WHY IT DOES IT:
    This provides a highly explainable, fast, and multi-tiered decision engine. It replaces
    RouteLLM's binary (strong/weak) routing by explicitly managing three distinct capability 
    paths (Local, Direct Cloud, Planner+Executor Cloud).
    """
    if not prompt or not prompt.strip():
        # Edge case: Empty prompt is trivial
        return {
            "tier": "SIMPLE",
            "path": 1,
            "method": "rule",
            "confidence": 1.0,
            "reason": "Empty prompt defaults to SIMPLE"
        }

    token_count = count_tokens(prompt)
    
    # Try Layer 1 (Rules)
    tier, path, reason = _layer_1_rules(prompt, token_count)
    
    if tier and path:
        return {
            "tier": tier,
            "path": path,
            "method": "rule",
            "confidence": 1.0, # Rules are strictly determinant
            "reason": reason
        }
        
    # Fallback to Layer 2 (Embeddings)
    tier, path, conf, reason = _layer_2_embeddings(prompt)
    
    return {
        "tier": tier,
        "path": path,
        "method": "embedding",
        "confidence": round(conf, 4),
        "reason": reason
    }

if __name__ == "__main__":
    test_prompts = [
        "What is an API?", # Expected: SIMPLE (Rule)
        "What are the differences between list and tuple in Python?", # Expected: MEDIUM (Embedding)
        "Design a microservices architecture for a real-time chat app", # Expected: COMPLEX (Rule - Keyword)
        "Please provide a 3 paragraph story about a dog." # Expected: MEDIUM (Embedding - length is probably 50-200, no complex kw)
    ]
    
    import json
    for p in test_prompts:
        result = classify(p)
        print(f"\nPrompt: '{p}'")
        print(json.dumps(result, indent=2))