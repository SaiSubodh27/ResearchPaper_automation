"""
Verification script for FastAPI endpoints /api/search-papers and /api/summarize-paper
"""

import asyncio
from fastapi.testclient import TestClient
from main import app

def test_fastapi_paper_endpoints():
    client = TestClient(app)
    
    print("--- 1. Testing POST /api/search-papers ---")
    payload = {
        "query": "transformer attention mechanisms",
        "limit": 5,
        "min_citations": 0
    }
    response = client.post("/api/search-papers", json=payload)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    print(f"Returned {data.get('count')} papers for query '{data.get('query')}':")
    for p in data.get("papers", []):
        j = p.get("journal", {})
        print(f"  - [{j.get('quartile')}] {p.get('title')} ({j.get('journal_name')})")

    assert len(data.get("papers", [])) > 0, "Should return at least 1 paper"
    print("[OK] /api/search-papers test passed!\n")

    print("--- 2. Testing POST /api/summarize-paper ---")
    sum_payload = {
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.",
        "journal_name": "NeurIPS",
        "quartile": "Q1"
    }
    sum_response = client.post("/api/summarize-paper", json=sum_payload)
    print(f"Status Code: {sum_response.status_code}")
    assert sum_response.status_code == 200
    sum_data = sum_response.json()
    print(f"Summary Title: {sum_data.get('title')}")
    print(f"Summary Content:\n{sum_data.get('summary')[:300]}...")
    print(f"Routing Metadata: {sum_data.get('routing_metadata')}")
    assert sum_data.get("summary") is not None
    print("[OK] /api/summarize-paper test passed!\n")

if __name__ == "__main__":
    test_fastapi_paper_endpoints()
