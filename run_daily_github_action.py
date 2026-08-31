"""
Standalone Runner Script for GitHub Actions Daily Automation
"""

import os
import json
import asyncio
import logging
import datetime
from paper_extractor import search_all_sources
from material_keywords import get_default_queries
from material_paper_store import save_material_papers, init_paper_db
from discord_notifier import send_discord_paper_notifications

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DAILY_JSON_PATH = os.path.join(DATA_DIR, "daily_material_papers.json")
HISTORY_JSON_PATH = os.path.join(DATA_DIR, "material_paper_history.json")


async def main():
    logger.info("=== Launching GitHub Actions Daily Material Science Paper Extractor ===")
    os.makedirs(DATA_DIR, exist_ok=True)
    await init_paper_db()

    queries = get_default_queries()
    extracted_papers = []

    for q in queries:
        try:
            logger.info(f"Extracting papers for query: '{q}'...")
            papers = await search_all_sources(query=q, limit=4)
            for p in papers:
                p["subfield"] = q
            extracted_papers.extend(papers)
        except Exception as e:
            logger.error(f"Error extracting for query '{q}': {e}")

    # Deduplicate extracted papers
    unique_papers = []
    seen = set()
    for p in extracted_papers:
        title_norm = p.get("title", "").strip().lower()
        if title_norm not in seen:
            seen.add(title_norm)
            unique_papers.append(p)

    logger.info(f"Total Unique Material Science Papers Extracted: {len(unique_papers)}")

    # 1. Save to SQLite database
    saved_sqlite = await save_material_papers(unique_papers)
    logger.info(f"Saved {saved_sqlite} new papers into SQLite database.")

    # 2. Write daily JSON feed (data/daily_material_papers.json)
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    daily_feed = {
        "updated_at": now_iso,
        "count": len(unique_papers),
        "papers": unique_papers
    }
    with open(DAILY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(daily_feed, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated daily JSON feed at: {DAILY_JSON_PATH}")

    # 3. Update historical JSON archive (data/material_paper_history.json)
    existing_history = []
    if os.path.exists(HISTORY_JSON_PATH):
        try:
            with open(HISTORY_JSON_PATH, "r", encoding="utf-8") as f:
                existing_history = json.load(f)
        except Exception:
            existing_history = []

    history_map = {p.get("title", "").lower(): p for p in existing_history}
    for p in unique_papers:
        history_map[p.get("title", "").lower()] = p

    updated_history = list(history_map.values())
    with open(HISTORY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_history, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated historical JSON feed at: {HISTORY_JSON_PATH} (Total archive: {len(updated_history)})")

    # 4. Trigger Discord Webhook Notification
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        logger.info("Posting Discord Webhook notification...")
        sent = await send_discord_paper_notifications(unique_papers, webhook_url=webhook_url, limit=5)
        logger.info(f"Discord notification status: {'Success' if sent else 'Failed'}")
    else:
        logger.info("No DISCORD_WEBHOOK_URL environment variable set. Skipping Discord post.")

    logger.info("=== GitHub Actions Daily Automation Finished Successfully ===")

if __name__ == "__main__":
    asyncio.run(main())
