"""
Extract recent papers and display complete journal quality & quartile info cleanly.
"""

import asyncio
import json
import sys

def safe_str(s: str) -> str:
    """Encodes string safely for Windows console printing."""
    return s.encode("ascii", "ignore").decode("ascii")

from paper_extractor import search_all_sources

async def run_extraction():
    queries = ["large language models", "cancer genomics", "deep learning"]
    all_extracted = []

    for q in queries:
        papers = await search_all_sources(query=q, limit=4, min_year=2026)
        all_extracted.extend(papers)

    print(f"Total Recent Papers Extracted: {len(all_extracted)}\n" + "="*80)

    for i, p in enumerate(all_extracted, 1):
        j = p["journal"]
        print(f"Paper #{i}")
        print(f"  Title: {safe_str(p['title'])}")
        print(f"  Authors: {safe_str(', '.join(p['authors']))}")
        print(f"  Source Database: {p['source_api']}")
        print(f"  Publication Year: {p['year']}")
        print(f"  Journal / Venue: {safe_str(j['journal_name'])}")
        print(f"  Peer-Reviewed: {'Yes' if j['is_peer_reviewed'] else 'No (Preprint)'}")
        print(f"  Quality Quartile: {j['quartile']} ({j['quality_tier']})")
        print(f"  Citation Score: {j['citation_score']}")
        print(f"  Citations Count: {p['citation_count']}")
        print(f"  DOI Link: {p['doi'] or 'N/A'}")
        print(f"  PDF Download URL: {p['pdf_url'] or 'N/A'}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run_extraction())
