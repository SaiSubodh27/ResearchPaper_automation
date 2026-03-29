I need you to generate the exact content, structure, and text for a 7-8 slide startup pitch deck about a project named **To-Path (Nexus Router)**. I will be feeding your output into Gamma.app (or another AI presentation maker) to generate the final slides, so please format your response slide-by-slide with clear headings, bullet points, and visual suggestions.

**Project Context:**
To-Path is a local-first API Routing system that uses "Prompt-Based Knowledge Distillation." It drastically cuts cloud API token bills (like Claude/GPT) by decoupling the "Brain" from the "Hands." It mathematically classifies prompts locally (Path 1). If a prompt is simple, it executes locally for free. If complex, it sends the prompt to a smart model to build a 150-token reasoning plan, then passes that logic to a free/cheap model (like Groq) to do the heavy 800+ token generation. It features a local proxy API (`/v1/chat/completions`) so any IDE can use it invisibly.

**Please structure the 8 slides exactly addressing these points:**

*   **Slide 1: The Initial Stage & The Problem:** What is the industry doing wrong? (Sledgehammer approach: using $15/1M token models for everything, wasting tokens on pleasantries, lack of dynamic routing).
*   **Slide 2: The Final Stage (What We Did):** What is To-Path? Explain the core concept: Cross-model cognitive routing, separating the Brain (Planner) from the Hands (Executor), and the local OpenAI-compatible proxy.
*   **Slide 3: Advantages vs. Disadvantages:** Highlight the massive cost savings and zero-downtime cascades (Advantages). Address the Time-to-First-Token delay and context fragmentation (Disadvantages).
*   **Slide 4: Overcoming the Disadvantages:** How did we fix the flaws? (Max-Output parameter clamping to stop AI "yapping", and Dynamic Context Sliding Windows using local AI to compress memory).
*   **Slide 5: The Competition & Our Edge:** What are competitors (like Manus or enterprise agents) doing? How do we beat them? (They are closed, expensive, and cloud-only. We are open-proxy, local-first, and heavily utilize free-tier API endpoints).
*   **Slide 6: The Innovation & Tech Stack (What we dared to do):** Explain the 3-path workflow. Detail the tech stack: Python, FastAPI, SentenceTransformers (MiniLM-L6), SQLite, Node.js React UI, and Litellm. 
*   **Slide 7: Trust, Scaling & Handling Large Outputs:** How can a company trust this? (100% private Path 1 execution). How do we handle massive outputs? (Streaming capabilities and forced structured JSON limits on the planner).
*   **Slide 8: The Next Final Steps:** What is the ultimate vision? (Semantic caching of embeddings, enterprise Docker deployments, expanding the "one-for-one sub path" to integrate specialized mathematical fallback agents).

**Constraint Checklist for Output:**
Keep it under 8 slides. Use powerful, startup-style "pitch" language. Be concise and use bullet points so Gamma can easily parse it into visual components. Do not output markdown code blocks, just raw structured text.