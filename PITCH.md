# To-Path: The Pitch

## The Problem (What the Industry is Doing)
- **Monolithic Cloud Dependency:** Developers are hardcoding expensive, single-model APIs (like Claude 3.5 Sonnet or GPT-4o) into their applications and bleeding cash on simple queries.
- **Sledgehammer Approach:** When a user asks "What is JSON?", the system sends it to a $15/1M token model. It's like hiring a Senior Staff Engineer to fix a typo.
- **"Yapping" Inefficiency:** Cloud models waste thousands of output tokens on conversational pleasantries ("Certainly! I can help with that...") before generating the actual code or answer you requested.
- **Wasted Context Overheads:** Users upload massive 50K+ token codebases in a single session. On every subsequent reply, they re-pay for all 50K back-and-forth tokens.
- **Vendor Lock-in & Downtime Risks:** If OpenAI or Anthropic goes offline, the entire product grinds to a halt.

## The Solution (What We Built)
- **Cognitive Routing & Cross-Model Prompt Distillation:** We decouple the "Brain" from the "Hands." Instead of one model doing everything, we force a smart model (Gemini Flash) to generate a miniature 150-token strict logic plan. We then inject that "mental model" into a lightning-fast, free-tier executor (Groq/Llama-3.3) to do the heavy 800+ token typing. 
- **Local-First Privacy:** We classify prompts locally using O(1) mathematical embedding vectors (`MiniLM-L6-v2`). If the task is simple (Path 1), we execute it locally via Ollama with 100% privacy and $0.00 infrastructure cost.
- **Max-Output Parameter Clamping:** We force the Executor model to drop the greetings, markdown wrappers, and pleasantries. It jumps straight into the output, saving up to 30% on token generation time and costs.
- **Zero-Downtime Cascading:** We built an auto-tumbling fallback system. If Mistral is offline, it fails over to Groq. If Groq hits a rate limit, it cascades to OpenRouter free models without throwing network errors to the user.
- **Invisible Interoperability:** We built standard OpenAI-compatible endpoints directly into the FastAPI backend (`/v1/chat/completions`). Any developer using Cline, Continue, or Cursor can simply swap their API base URL to our server and instantly receive our routing benefits without writing a line of code.
- **Dynamic Context Compression (Sliding Window):** Our background `memory.py` monitors session token lengths via a local SQLite DB. When a session exceeds bounds, the system utilizes the free Path 1 local model to compress message history into tight paragraphs, preserving token ceilings.