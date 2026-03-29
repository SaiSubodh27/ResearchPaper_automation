import asyncio
import httpx
import uuid

API_BASE = "http://localhost:8000"

def print_help():
    print("""
    [Planner-Executor CLI Client]
    Interactive mode options:
    - Type any question to send it to the unified Router endpoint.
    - Type 'stats'     : View ROI and path-usage tracking for your session.
    - Type 'history'   : List the recent context items for your session.
    - Type 'clear'     : Wipe the current session state.
    - Type 'exit'      : Quit.
    """)

async def run_cli():
    # Force a unique session on start
    session_id = str(uuid.uuid4())[:8]
    print(f"Initiated Shell Interface. [Session ID: {session_id}]")
    print_help()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            try:
                user_msg = input(f"\nUser [{session_id}] > ")
                user_msg = user_msg.strip()
                
                if not user_msg:
                    continue
                    
                if user_msg.lower() == 'exit':
                    break
                elif user_msg.lower() == 'stats':
                    r = await client.get(f"{API_BASE}/session/{session_id}/stats")
                    print("\n--- Session Cost Statistics ---")
                    print(r.json())
                    continue
                elif user_msg.lower() == 'history':
                    r = await client.get(f"{API_BASE}/session/{session_id}/history")
                    print("\n--- Session Memory Window ---")
                    for mh in r.json():
                        print(f"[{mh['role']}] {mh['content'][:100]}...")
                    continue
                elif user_msg.lower() == 'clear':
                    r = await client.delete(f"{API_BASE}/session/{session_id}")
                    print("\n--- Session Cleared ---")
                    continue
                    
                # Standard routing POST
                print("... Routing ...", end='\r')
                response = await client.post(
                    f"{API_BASE}/chat",
                    json={"message": user_msg, "session_id": session_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print("\n" + "="*50)
                    print(f"PATH USED: {data['path_used']} ({data['routing_tier']})")
                    print(f"REASON:    {data['routing_reason']}")
                    print(f"MODEL:     {data['model_used']}")
                    print(f"COST:      ${data['total_cost_usd']:.6f} | Tokens: {data['tokens_used']}")
                    if data['fallback_triggered']:
                        print(f"[!] FALLBACK: {data['fallback_reason']}")
                    print("="*50 + "\n")
                    
                    print(data['response'])
                else:
                    print(f"\nHTTP ERROR: {response.status_code} - {response.text}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"CLI Client Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_cli())
