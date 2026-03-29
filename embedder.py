import os
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

# Configuration for the embedder
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Initialize the model once when the module is loaded
# This prevents reloading the model for every function call, improving latency
try:
    model = SentenceTransformer(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Failed to load sentence-transformers model '{MODEL_NAME}': {e}")

def complexity_embedding(prompt: str) -> np.ndarray:
    """
    Generates a dense vector embedding for a given text prompt.
    
    WHAT IT DOES:
    Uses a local sentence-transformer model (default: all-MiniLM-L6-v2) to convert 
    the input string into a high-dimensional numpy array representing its semantic meaning.
    
    WHY IT DOES IT:
    By using a local open-source model, we eliminate the dependency on OpenAI's paid 
    embedding API for RouteLLM. These embeddings are used downstream by the routing 
    decision matrix to evaluate the complexity of the prompt and decide whether to 
    route to our local Ollama models or the cloud-based Claude API.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")
    
    # encode returns a numpy array of the text features
    return model.encode(prompt)

def similarity_score(prompt_a: str, prompt_b: str) -> float:
    """
    Calculates the cosine similarity between two text prompts.
    
    WHAT IT DOES:
    Embeds both prompts into vectors and computes the cosine similarity score 
    (ranging from -1.0 to 1.0) between their vector representations using scikit-learn.
    
    WHY IT DOES IT:
    This allows the system to compare incoming prompts against a cache of previously 
    routed or evaluated prompts. Understanding prompt similarity enables heuristic 
    caching (bypassing the router entirely if an exact semantic match exists) and 
    helps in memory summarization decisions.
    """
    emb_a = complexity_embedding(prompt_a).reshape(1, -1)
    emb_b = complexity_embedding(prompt_b).reshape(1, -1)
    
    score = cosine_similarity(emb_a, emb_b)[0][0]
    return float(score)

if __name__ == "__main__":
    print(f"Loaded Local Embedding Model: {MODEL_NAME}")
    
    # 3 example prompts showing different intents and complexities
    example_prompts = [
        "What is the capital of France?",
        "Write a simple python script to read a CSV file.",
        "Explain the architectural differences between a Transformer and an LSTM, focusing on the mathematical formulation of their attention mechanisms and vanishing gradients."
    ]
    
    print("\n--- Generating Embeddings ---")
    for i, p in enumerate(example_prompts):
        emb = complexity_embedding(p)
        print(f"\nPrompt {i+1}: '{p}'")
        print(f"Shape: {emb.shape}")
        print(f"First 5 vector values: {emb[:5]}")
        
    print("\n--- Testing Similarity Scores ---")
    score_1_2 = similarity_score(example_prompts[0], example_prompts[1])
    score_2_3 = similarity_score(example_prompts[1], example_prompts[2])
    score_1_3 = similarity_score(example_prompts[0], example_prompts[2])
    
    print(f"Similarity (Prompt 1 vs 2): {score_1_2:.4f}")
    print(f"Similarity (Prompt 2 vs 3): {score_2_3:.4f}")
    print(f"Similarity (Prompt 1 vs 3): {score_1_3:.4f}")
