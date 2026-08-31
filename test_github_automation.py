"""
Verification script for GitHub Actions Runner and Discord Notifier module.
"""

import os
import sys
import json
import asyncio

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def safe_str(s: str) -> str:
    return s.encode("ascii", "ignore").decode("ascii")

from discord_notifier import format_paper_embed, send_discord_paper_notifications
from run_daily_github_action import main as run_github_action

async def test_automation():
    print("--- 1. Testing Discord Embed Formatter ---")
    dummy_paper = {
        "title": "Perovskite Solar Cells with High Efficiency and Stability",
        "authors": ["Alice Smith", "Bob Jones"],
        "year": 2026,
        "citation_count": 45,
        "doi": "https://doi.org/10.1038/s41586-026-00001-x",
        "pdf_url": "https://www.nature.com/articles/s41586-026-00001-x.pdf",
        "source_api": "OpenAlex",
        "journal": {
            "journal_name": "Nature Energy",
            "quartile": "Q1",
            "quality_tier": "Top-Tier (Q1)"
        },
        "ai_summary": "Demonstrates a novel halide perovskite passivation layer yielding 26.5% power conversion efficiency."
    }
    
    embed = format_paper_embed(dummy_paper)
    print(f"Formatted Embed Title: {safe_str(embed['title'])}")
    print(f"Formatted Embed Description: {safe_str(embed['description'])}")
    assert embed["title"].startswith("🔬")
    assert embed["color"] == 0x2ECC71  # Q1 green
    print("[OK] Discord Embed Formatter test passed!\n")

    print("--- 2. Testing GitHub Actions Runner Execution ---")
    await run_github_action()
    
    daily_path = os.path.join(os.path.dirname(__file__), "data", "daily_material_papers.json")
    assert os.path.exists(daily_path), "daily_material_papers.json must be generated"
    
    with open(daily_path, "r", encoding="utf-8") as f:
        feed = json.load(f)
        
    print(f"Generated JSON feed with {feed.get('count')} papers (Updated at: {feed.get('updated_at')})")
    assert feed.get("count", 0) > 0, "JSON feed should contain extracted papers"
    print("[OK] GitHub Actions Runner execution test passed!\n")

if __name__ == "__main__":
    asyncio.run(test_automation())
