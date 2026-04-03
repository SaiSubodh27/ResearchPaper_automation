import streamlit as st
import requests
import uuid
import json

# Local FastAPI Backend URL
API_BASE = "http://localhost:8000"

st.set_page_config(page_title="AI Planner-Executor System", page_icon="🧠", layout="wide")

# Concept Explanation text for the user
with st.expander("ℹ️ How does this Transfer Learning / Orchestration concept work?"):
    st.markdown("""
    **Are we changing the integrities of the models?**
    *No.* We are not doing fine-tuning or changing the internal weights of the models. We have built a **Smart Concept Wrapper (Orchestration Layer)**.

    **How does the execution work? (Prompt-Based Distillation)**
    1. **Layer 1 (The Classifier):** When you type a prompt, our local `embedder.py` (MiniLM) calculates the mathematical complexity.
    2. **Layer 2 (The Router):** Depending on the complexity, it routes you between three paths dynamically to save money:
        * **Path 1 (Simple):** Sends directly to your local, free model (Mistral).
        * **Path 2 (Medium):** Sends directly to the relatively cheap cloud model (Gemini).
        * **Path 3 (Complex):** This is the **Brain** concept. We send your prompt to an expensive model (Claude 3.5 Sonnet) but heavily restrict it to *only generate a master plan*. Then, we dynamically inject that plan into a new prompt and give it to Gemini to actually write the code based on Claude's blueprint.
        
    This gives you "Teacher Quality" at "Student Prices" without altering the models themselves!
    """)

# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar for Metrics ---
st.sidebar.title("System Diagnostics")
st.sidebar.caption(f"Session ID: `{st.session_state.session_id}`")

# Fetch Stats Function
def fetch_stats():
    try:
        r = requests.get(f"{API_BASE}/session/{st.session_state.session_id}/stats", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "total_cost_usd" in data:
                return data
    except Exception:
        pass
    return None

if st.sidebar.button("Clear Session History Data"):
    try:
        requests.delete(f"{API_BASE}/session/{st.session_state.session_id}")
    except:
        pass
    st.session_state.messages = []
    # Force new UUID
    st.session_state.session_id = str(uuid.uuid4())[:8]
    st.rerun()

st.sidebar.divider()

stats = fetch_stats()
if stats:
    st.sidebar.subheader("Live ROI Tracking")
    st.sidebar.metric(label="Actual Total Cost", value=f"${stats['total_cost_usd']:.5f}")
    st.sidebar.metric(label="Total Savings vs Cloud", value=f"${stats['savings_usd']:.5f} ({stats['savings_percent']}%)")
    
    st.sidebar.divider()
    st.sidebar.subheader("ROI Visual Proof")
    # Massive bar chart comparing Claude alone vs Our Routing Cost
    st.sidebar.bar_chart({
        "Cost Comparison": {
            "If using Claude Sonnet": stats['cost_if_all_claude_sonnet'],
            "Actual Routed Cost": stats['total_cost_usd']
        }
    }, height=200, color="#17fc03")

    st.sidebar.caption("Where your prompts went:")
    st.sidebar.text(f"Path 1 (Local): {stats.get('path1_calls', 0)}")
    st.sidebar.text(f"Path 2 (Direct): {stats.get('path2_calls', 0)}")
    st.sidebar.text(f"Path 3 (Planner): {stats.get('path3_calls', 0)}")
else:
    st.sidebar.caption("No queries run yet in this session.")

# --- Main Chat UI ---
st.title("🧠 Multi-Tier Router Interface")

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If it's an assistant message and has metadata, show the debug expander
        if "metadata" in msg and msg["metadata"]:
            with st.expander("🔍 Show Routing Decision & Execution Logs"):
                meta = msg["metadata"]
                st.code(json.dumps({
                    "Path Triggered": f"Path {meta.get('path_used')}",
                    "Tier Evaluated": meta.get('routing_tier'),
                    "Reason": meta.get('routing_reason'),
                    "Model Matrix Triggered": meta.get('model_used'),
                    "Cost Execution": f"${meta.get('total_cost_usd'):.5f}",
                    "Fallback Used": meta.get('fallback_triggered')
                }, indent=2), language="json")

# Input Box
if prompt := st.chat_input("Enter your request here..."):
    # Render user prompt locally
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Backend API
    with st.chat_message("assistant"):
        with st.spinner("Routing prompt through intelligence matrix..."):
            try:
                response = requests.post(f"{API_BASE}/chat", json={
                    "message": prompt,
                    "session_id": st.session_state.session_id
                }, timeout=120)

                if response.status_code == 200:
                    data = response.json()
                    final_text = data.get("response", "No response.")
                    st.markdown(final_text)
                    
                    # Store message and metadata
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": final_text,
                        "metadata": data
                    })
                    
                    st.rerun() # Refresh sidebar stats
                else:
                    st.error(f"API Error {response.status_code}: {response.text}")
                    st.warning("Make sure your API server is running (`python -m uvicorn main:app --host 0.0.0.0 --port 8000`)")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API Server. Is `uvicorn` running in the background?")
                st.code("python -m uvicorn main:app --host 0.0.0.0 --port 8000")
