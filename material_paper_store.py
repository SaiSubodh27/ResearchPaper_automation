"""
SQLite Persistent Storage Layer for Material Science Papers
"""

import os
import json
import logging
import datetime
import aiosqlite
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "sessions.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_material_papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    authors TEXT,
    year INTEGER,
    date_published TEXT,
    journal_name TEXT,
    quartile TEXT,
    citation_score REAL,
    citation_count INTEGER,
    doi TEXT,
    pdf_url TEXT,
    source_api TEXT,
    ai_summary TEXT,
    subfield TEXT,
    fetched_at TEXT
);
"""

async def init_paper_db():
    """Initializes the daily_material_papers table in SQLite."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()
    logger.info("Initialized daily_material_papers SQLite storage.")


async def save_material_papers(papers: List[Dict[str, Any]]) -> int:
    """
    Saves a list of paper dictionaries into SQLite, ignoring duplicates based on ID or DOI.
    Returns the count of newly saved papers.
    """
    await init_paper_db()
    saved_count = 0
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        for p in papers:
            paper_id = p.get("id") or p.get("doi") or p.get("title")
            authors_json = json.dumps(p.get("authors", []))
            journal = p.get("journal", {})

            try:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO daily_material_papers (
                        id, title, abstract, authors, year, date_published,
                        journal_name, quartile, citation_score, citation_count,
                        doi, pdf_url, source_api, ai_summary, subfield, fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paper_id,
                        p.get("title"),
                        p.get("abstract", ""),
                        authors_json,
                        p.get("year"),
                        str(p.get("year") or ""),
                        journal.get("journal_name", "Academic Journal"),
                        journal.get("quartile", "Q2"),
                        journal.get("citation_score", 0.0),
                        p.get("citation_count", 0),
                        p.get("doi", ""),
                        p.get("pdf_url", ""),
                        p.get("source_api", "Unknown"),
                        p.get("ai_summary", ""),
                        p.get("subfield", "Material Science"),
                        now_str
                    )
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving paper {paper_id}: {e}")

        await db.commit()
    return saved_count


async def get_today_material_papers(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches the most recently stored Material Science papers."""
    await init_paper_db()
    papers = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM daily_material_papers
            ORDER BY fetched_at DESC, citation_count DESC
            LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                p_dict = dict(r)
                if p_dict.get("authors"):
                    try:
                        p_dict["authors"] = json.loads(p_dict["authors"])
                    except Exception:
                        pass
                papers.append(p_dict)
    return papers


async def query_paper_history(
    keyword: Optional[str] = None,
    quartile: Optional[str] = None,
    min_year: Optional[int] = None,
    min_citations: int = 0,
    limit: int = 30
) -> List[Dict[str, Any]]:
    """Queries historical Material Science papers with filters."""
    await init_paper_db()
    sql = "SELECT * FROM daily_material_papers WHERE 1=1"
    params = []

    if keyword:
        sql += " AND (title LIKE ? OR abstract LIKE ? OR journal_name LIKE ?)"
        kw_param = f"%{keyword}%"
        params.extend([kw_param, kw_param, kw_param])
    if quartile:
        sql += " AND quartile = ?"
        params.append(quartile)
    if min_year:
        sql += " AND year >= ?"
        params.append(min_year)
    if min_citations > 0:
        sql += " AND citation_count >= ?"
        params.append(min_citations)

    sql += " ORDER BY year DESC, citation_count DESC LIMIT ?"
    params.append(limit)

    papers = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            for r in rows:
                p_dict = dict(r)
                if p_dict.get("authors"):
                    try:
                        p_dict["authors"] = json.loads(p_dict["authors"])
                    except Exception:
                        pass
                papers.append(p_dict)
    return papers
