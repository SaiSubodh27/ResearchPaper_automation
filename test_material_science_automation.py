"""
Verification script for Material Science automated ingestion, SQLite persistence, and REST endpoints.
"""

import sys
import asyncio
from fastapi.testclient import TestClient

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def safe_str(s: str) -> str:
    """Safe ASCII string conversion for Windows console."""
    return s.encode("ascii", "ignore").decode("ascii")

from main import app
from material_paper_store import init_paper_db, get_today_material_papers, query_paper_history
from daily_scheduler import run_daily_material_ingestion

async def test_material_ingestion_and_store():
    print("--- 1. Testing Material Science Ingestion & SQLite Store ---")
    await init_paper_db()
    
    res = await run_daily_material_ingestion(limit_per_query=2)
    print(f"Ingestion result: Processed {res['processed_count']}, Saved {res['saved_count']}")
    
    today_papers = await get_today_material_papers(limit=5)
    print(f"Retrieved {len(today_papers)} papers from SQLite store:")
    for p in today_papers:
        print(f"  - [{p.get('quartile')}] {safe_str(p.get('title'))} ({safe_str(p.get('journal_name'))})")
    
    assert len(today_papers) > 0, "SQLite store should contain at least 1 ingested paper"
    print("[OK] Ingestion and Store test passed!\n")

def test_fastapi_material_endpoints():
    client = TestClient(app)
    
    print("--- 2. Testing GET /api/material-science/daily ---")
    resp_daily = client.get("/api/material-science/daily")
    print(f"Daily Endpoint Status: {resp_daily.status_code}")
    assert resp_daily.status_code == 200
    daily_data = resp_daily.json()
    print(f"Daily endpoint returned {daily_data.get('count')} papers.")
    assert len(daily_data.get("papers", [])) > 0
    print("[OK] GET /api/material-science/daily test passed!\n")

    print("--- 3. Testing GET /api/material-science/history ---")
    resp_hist = client.get("/api/material-science/history?quartile=Q1")
    print(f"History Endpoint Status: {resp_hist.status_code}")
    assert resp_hist.status_code == 200
    hist_data = resp_hist.json()
    print(f"History endpoint returned {hist_data.get('count')} Q1 papers.")
    print("[OK] GET /api/material-science/history test passed!\n")

    print("--- 4. Testing POST /api/material-science/scrape (On-Demand Scrape) ---")
    scrape_payload = {
        "query": "solid state battery electrolytes",
        "limit": 3
    }
    resp_scrape = client.post("/api/material-science/scrape", json=scrape_payload)
    print(f"Scrape Endpoint Status: {resp_scrape.status_code}")
    assert resp_scrape.status_code == 200
    scrape_data = resp_scrape.json()
    print(f"Scraped {scrape_data.get('extracted_count')} papers for query '{scrape_data.get('query')}'.")
    print("[OK] POST /api/material-science/scrape test passed!\n")

if __name__ == "__main__":
    asyncio.run(test_material_ingestion_and_store())
    test_fastapi_material_endpoints()
