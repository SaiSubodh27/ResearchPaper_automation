# Embedder Implementation Summary

## What Was Done
1. Created the `embedder.py` module, which serves as the local-first embedding engine for the AI routing system.
2. Created a `.env` file to manage the environment configuration (specifically the `EMBEDDING_MODEL_NAME`).
3. Set up the module to be easily testable via a CLI `__main__` block as requested.

## How It Was Done
- **Dependencies**: Utilized `sentence-transformers` for local model loading and vectorization, `python-dotenv` for configuration management, and `scikit-learn` for generating cosine similarity scores.
- **Model Choice**: Initialized `SentenceTransformer` using the `all-MiniLM-L6-v2` model as the default. The model is initialized globally within the module so it only loads into memory once per session, ensuring low latency on sub-sequential calls.
- **Core Functions**:
  - `complexity_embedding(prompt)`: Takes a string and returns a dense numpy array representation of its semantic meaning.
  - `similarity_score(prompt_a, prompt_b)`: Wraps the embedding generation and computes the `cosine_similarity` between the two resulting vectors.
- **Docstrings**: Both functions include comprehensive `WHAT IT DOES` and `WHY IT DOES IT` sections to explain their functionality and purpose in the broader system architecture.
- **Testing**: Added a `__main__` block with 3 targeted example prompts (factual, coding, complex architectural explanation) to display array shapes, sample vector values, and similarity comparisons.

## Why It Was Done (Strategic Context)
- This module completely replaces RouteLLM's standard requirement for an OpenAI API key.
- By performing embeddings locally, we guarantee zero monetary cost for routing decisions, increased privacy for user inputs, and support for the overarching "LOCAL-FIRST" goal of this system. These vector representations will feed directly into the custom classifier for prompt-complexity scoring in the next phase.