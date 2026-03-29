# To-Path

A highly efficient, local-first API Router that uses **Prompt-Based Knowledge Distillation** to slash cloud AI bills. The platform intelligently routes queries between extremely small/free local AI models (Path 1), ultra-fast free-tier executors (Path 2), and high-reasoning smart planners (Path 3).

## The Core Concept
Instead of paying a heavy model (Claude 3.5 Sonnet / GPT-4o) to do all the typing, we split the "Brain" from the "Hands."
If a prompt is complex, we pay a tiny amount for the "Brain" (`Gemini Flash`) to generate a rigid logic structure in JSON. Then we feed that logical structure into the "Hands" (`Groq/Llama-3.3`), forcing a free model to adopt the reasoning capabilities of a smart model. 

---

## 1. What's Included?
1. **The Core Router (`main.py`):** A FastAPI backend that hosts the embedding classifier, cost estimators, and routing logic. 
2. **The Proxy API (`/v1/chat/completions`):** A native drop-in replacement for OpenAI. Any tool (Cursor, VS Code, Chat UIs) can point here instead of OpenAI.
3. **The Web UI (`/web_ui`):** A beautiful Node.js/React-style frontend to visualize your routing diagnostics and cost savings in real-time.
4. **Docker Deployment:** Fully containerized setup.

---

## 2. Setup & Installation (Local Development)

### Prerequisites:
- Python 3.11+
- Node.js & NPM (for the UI)
- Ollama (for the Path 1 Local model)

### Step 1: Clone and install backend
```bash
git clone <repository_url>
cd router
pip install -r requirements.txt
```

### Step 2: Set your API Keys
Create a `.env` file in the root directory (based on the provided `.env.example` if applicable) and add your keys:
```
GROQ_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
LOCAL_MODEL=ollama/qwen2.5:0.5b
```

### Step 3: Install Local Model
Ensure Ollama is running on your machine, then pull the local routing model:
```bash
ollama pull qwen2.5:0.5b
```

### Step 4: Run the servers
**Run the Backend Engine:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
**Run the Frontend UI:**
```bash
cd web_ui
npm install
node server.js
```
The UI will now be live at `http://localhost:3000`.

---

## 3. How to Use the API (OpenAI Proxy Integration)

We built an API endpoint that exactly mimics OpenAI. This means you do **NOT** need to build a custom frontend if you already use an AI editor. 

### To use this in VS Code (Cline / Continue) or Cursor:
1. Open your LLM settings in the tool.
2. Under **Model Provider**, choose "Custom Proxy" or "OpenAI Compatible".
3. Set the **API Base URL** to: `http://127.0.0.1:8000/v1`
4. Set the **API Key** to: `sk-dummy-key`
5. Type any prompt. The router will intercept it, classify it, execute it via the cheapest path, and return it directly into your IDE.

---

## 4. How the Workflow Operates (End-to-End)

1. **Ingestion:** User sends a prompt (e.g. "Create a fastAPI server.") via UI or IDE API.
2. **Classification (Layer 1):** The `classifier.py` checks token count and keywords. If trivial, routes to **Path 1 (Local Ollama)**. 
3. **Classification (Layer 2):** If ambiguous, the prompt is vectorized using `MiniLM` embeddings and measured via Cosine Similarity to route to Path 2 or 3.
4. **Execution - Path 2 (Simple Cloud):** Routes to `Groq Llama-3.3`. The prompt is mathematically clamped to prevent "Yapping" and output only the required data.
5. **Execution - Path 3 (Complex Distillation):** 
   - *Planner Phase:* `Gemini` generates a 150-token strict JSON output detailing reasoning chains, constraints, and failure modes.
   - *Executor Phase:* That logic JSON is injected into `Groq Llama-3.3`, which executes the heavy lifting.
6. **Cost Tracking & Memory Compression:** The session metrics (Cost saved, tokens used) are saved to an async `SQLite` database. Once the DB sees the token context getting too large, Path 1 quietly compresses the old memory history to prevent bloat.

---

## 5. Deployment Info (Docker)

To deploy this in an enterprise environment or a cloud server:
Ensure Docker daemon is running on your server.
```bash
docker-compose up --build -d
```
The backend API will be bound to port `8000` and the UI to port `3000`.