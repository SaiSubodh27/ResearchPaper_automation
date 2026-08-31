"""
Discord Webhook Notification Module for Daily Material Science Papers
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Color codes for Discord Embeds
QUARTILE_COLORS = {
    "Q1": 0x2ECC71,  # Emerald Green
    "Q2": 0x3498DB,  # Ocean Blue
    "Q3": 0xF1C40F,  # Amber Yellow
    "Q4": 0xE67E22,  # Warm Orange
    "Preprint (Unranked)": 0x95A5A6  # Cool Slate Gray
}


def format_paper_embed(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a paper metadata dictionary into a rich Discord embed object."""
    journal = paper.get("journal", {})
    quartile = journal.get("quartile", "Q2")
    color = QUARTILE_COLORS.get(quartile, 0x3498DB)

    title = paper.get("title", "Untitled Paper")
    authors = ", ".join(paper.get("authors", [])) or "Unknown Authors"
    if len(authors) > 200:
        authors = authors[:197] + "..."

    journal_name = journal.get("journal_name", "Academic Journal")
    quality_tier = journal.get("quality_tier", f"Peer-Reviewed ({quartile})")
    citation_count = paper.get("citation_count", 0)

    abstract = paper.get("ai_summary") or paper.get("abstract") or "No summary available."
    if len(abstract) > 350:
        abstract = abstract[:347] + "..."

    doi_url = paper.get("doi") or "N/A"
    pdf_url = paper.get("pdf_url") or "N/A"

    embed = {
        "title": f"🔬 {title[:250]}",
        "description": f"**Abstract / AI Summary:**\n{abstract}",
        "color": color,
        "fields": [
            {
                "name": "🏛️ Journal / Venue",
                "value": f"**{journal_name}**\nTag: `{quality_tier}`",
                "inline": True
            },
            {
                "name": "📊 Metrics",
                "value": f"Citations: **{citation_count}**\nSource: `{paper.get('source_api', 'Multi-Source')}`",
                "inline": True
            },
            {
                "name": "👥 Authors",
                "value": authors,
                "inline": False
            },
            {
                "name": "🔗 Links & PDF",
                "value": f"[[DOI Link]]({doi_url})" + (f" • [[Download PDF]]({pdf_url})" if pdf_url != "N/A" else ""),
                "inline": False
            }
        ],
        "footer": {
            "text": f"Material Science Automation • Ingested Year {paper.get('year') or 2026}"
        }
    }
    return embed


async def send_discord_paper_notifications(
    papers: List[Dict[str, Any]], webhook_url: Optional[str] = None, limit: int = 5
) -> bool:
    """
    Sends rich paper embed notifications to Discord Webhook.
    """
    url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
    if not url or not url.startswith("http"):
        logger.warning("DISCORD_WEBHOOK_URL is not configured or invalid. Skipping Discord alert.")
        return False

    papers_to_send = papers[:limit]
    embeds = [format_paper_embed(p) for p in papers_to_send]

    payload = {
        "content": f"🚀 **Daily Material Science Research Alert** — Extracted **{len(papers)}** new papers today!",
        "embeds": embeds
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code in [200, 204]:
                logger.info(f"Successfully posted {len(embeds)} paper embeds to Discord webhook!")
                return True
            else:
                logger.error(f"Discord Webhook error {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Discord webhook notification: {e}")
        return False
