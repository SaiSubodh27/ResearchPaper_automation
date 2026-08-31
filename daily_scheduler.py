"""
Automated Daily Ingestion Scheduler for Material Science Papers
"""

import asyncio
import datetime
import logging
from typing import List, Dict, Any
from paper_extractor import search_all_sources
from material_keywords import get_default_queries
from material_paper_store import save_material_papers, init_paper_db
from router import route_request

logger = logging.getLogger(__name__)

# Configurable daily trigger hour (Default: 00:00 Midnight UTC)
TARGET_RUN_HOUR_UTC = 0


async def run_daily_material_ingestion(limit_per_query: int = 4) -> Dict[str, Any]:
    """
    Executes automated paper ingestion for Material Science topics.
    Searches multi-source APIs, attaches journal Q1-Q4 quartiles, generates AI summaries,
    and stores new unique papers into SQLite daily_material_papers table.
    """
    logger.info("--- Starting Automated Material Science Daily Paper Ingestion ---")
    await init_paper_db()

    queries = get_default_queries()
    all_papers = []

    for query in queries:
        try:
            papers = await search_all_sources(query=query, limit=limit_per_query)
            for p in papers:
                p["subfield"] = query
            all_papers.extend(papers)
        except Exception as e:
            logger.error(f"Error fetching Material Science query '{query}': {e}")

    # Generate quick AI summaries for top Q1/Q2 papers
    for p in all_papers[:5]:
        if p.get("abstract") and not p.get("ai_summary"):
            try:
                summary_prompt = (
                    f"Summarize key material properties & findings from this abstract:\n"
                    f"Title: {p.get('title')}\nAbstract: {p.get('abstract')[:400]}"
                )
                res = await route_request(summary_prompt, session_id="daily-ingestion-summary")
                p["ai_summary"] = res.get("response", "")
            except Exception as e:
                logger.warning(f"Could not generate AI summary for '{p.get('title')}': {e}")

    saved_count = await save_material_papers(all_papers)
    logger.info(f"--- Completed Daily Ingestion: Processed {len(all_papers)} papers, Saved {saved_count} new entries ---")

    return {
        "status": "success",
        "processed_count": len(all_papers),
        "saved_count": saved_count
    }


def _seconds_until_target_hour(target_hour_utc: int = 0) -> float:
    """Calculates exact seconds remaining until the next occurrence of target_hour_utc."""
    now = datetime.datetime.now(datetime.timezone.utc)
    target = now.replace(hour=target_hour_utc, minute=0, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


async def _daily_loop():
    """
    Background task loop that:
    1. Executes an initial ingestion on startup.
    2. Calculates time remaining until 00:00 Midnight UTC every day and triggers automatically.
    """
    logger.info("Executing initial startup paper ingestion sync...")
    try:
        await run_daily_material_ingestion()
    except Exception as e:
        logger.error(f"Error in initial startup paper ingestion: {e}")

    while True:
        seconds_to_wait = _seconds_until_target_hour(TARGET_RUN_HOUR_UTC)
        next_run_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds_to_wait)
        logger.info(f"Next automated Material Science paper ingestion scheduled at: {next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (in {round(seconds_to_wait/3600, 2)} hours)")

        await asyncio.sleep(seconds_to_wait)

        try:
            await run_daily_material_ingestion()
        except Exception as e:
            logger.error(f"Error during scheduled daily paper ingestion: {e}")


def start_background_scheduler():
    """Starts the non-blocking daily ingestion task in the asyncio event loop."""
    logger.info("Launching background Material Science paper scheduler...")
    asyncio.create_task(_daily_loop())
