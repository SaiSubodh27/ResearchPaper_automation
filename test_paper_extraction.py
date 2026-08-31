"""
Test suite for Paper Extraction and Journal Quartile Quality Ranking engine.
"""

import asyncio
import json
from journal_ranker import evaluate_journal_quality
from paper_extractor import search_all_sources

def test_journal_ranker():
    print("--- 1. Testing Journal Quality Ranker ---")
    top_v = {"name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "2yr_mean_citedness": 15.2, "h_index": 200, "type": "journal"}
    eval_top = evaluate_journal_quality(top_v)
    print(f"Top Venue: {eval_top['journal_name']} -> Quartile: {eval_top['quartile']} ({eval_top['quality_tier']})")
    assert eval_top["quartile"] == "Q1"

    mid_v = {"name": "Journal of Applied Science", "2yr_mean_citedness": 2.2, "h_index": 50, "type": "journal"}
    eval_mid = evaluate_journal_quality(mid_v)
    print(f"Mid Venue: {eval_mid['journal_name']} -> Quartile: {eval_mid['quartile']} ({eval_mid['quality_tier']})")
    assert eval_mid["quartile"] == "Q2"

    prep_v = {"name": "arXiv Preprint", "type": "repository"}
    eval_prep = evaluate_journal_quality(prep_v, is_preprint=True)
    print(f"Preprint: {eval_prep['journal_name']} -> Quartile: {eval_prep['quartile']} ({eval_prep['quality_tier']})")
    assert eval_prep["quartile"] == "Preprint (Unranked)"
    print("[OK] Journal Ranker tests passed!\n")

async def test_paper_extractor():
    print("--- 2. Testing Multi-Source Paper Search (OpenAlex, Semantic Scholar, arXiv) ---")
    query = "deep learning transformers"
    print(f"Searching query: '{query}'...")
    
    papers = await search_all_sources(query=query, limit=6)
    print(f"Found {len(papers)} papers across sources.\n")

    for i, p in enumerate(papers, 1):
        j = p["journal"]
        print(f"[{i}] {p['title']}")
        print(f"    Source: {p['source_api']} | Year: {p['year']} | Citations: {p['citation_count']}")
        print(f"    Journal: {j['journal_name']} | Quality: {j['quartile']} ({j['quality_tier']}) | Score: {j['citation_score']}")
        print(f"    DOI: {p.get('doi')} | PDF: {'Yes' if p.get('pdf_url') else 'No'}\n")

    assert len(papers) > 0, "Should return at least 1 paper"
    print("[OK] Paper Extractor tests passed!\n")

if __name__ == "__main__":
    test_journal_ranker()
    asyncio.run(test_paper_extractor())
