"""
Multi-Source Academic Paper Extraction Engine

Extracts peer-reviewed journal papers and preprints from OpenAlex, Europe PMC,
Crossref, Semantic Scholar, and arXiv APIs.
Enriches every paper with journal details, citation metrics, open-access PDF URLs,
and Q1-Q4 journal quality rankings via journal_ranker.py.
"""

import re
import xml.etree.ElementTree as ET
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from journal_ranker import evaluate_journal_quality

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "PaperAutomationBot/1.0 (mailto:subodh@research.org)"}


def _reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
    """Reconstructs full abstract text from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join([w[1] for w in word_positions])


def _normalize_title(title: str) -> str:
    """Normalizes title string for deduplication."""
    return re.sub(r"[^\w\s]", "", title.lower()).strip()


async def fetch_openalex_papers(
    query: str, limit: int = 10, min_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetches peer-reviewed journal & conference papers from OpenAlex API."""
    papers = []
    url = f"https://api.openalex.org/works?search={query}&per-page={limit}"
    if min_year:
        url += f"&filter=publication_year:>{min_year - 1}"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                logger.warning(f"OpenAlex API returned status {resp.status_code}")
                return papers
            data = resp.json()
            results = data.get("results", [])

            for item in results:
                title = item.get("display_name") or item.get("title") or ""
                if not title:
                    continue

                abstract = _reconstruct_openalex_abstract(item.get("abstract_inverted_index"))
                
                authorships = item.get("authorships", [])
                authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in authorships
                    if a.get("author", {}).get("display_name")
                ]

                primary_loc = item.get("primary_location") or {}
                source = primary_loc.get("source") or {}
                venue_data = {
                    "name": source.get("display_name") or "Unknown Venue",
                    "type": source.get("type") or item.get("type") or "journal",
                    "2yr_mean_citedness": source.get("summary_stats", {}).get("2yr_mean_citedness", 0.0),
                    "h_index": source.get("summary_stats", {}).get("h_index", 0),
                    "publisher": source.get("publisher") or "",
                    "cited_by_count": item.get("cited_by_count", 0)
                }

                journal_info = evaluate_journal_quality(venue_data, is_preprint=(item.get("type") == "repository"))
                oa_info = item.get("open_access") or {}
                pdf_url = oa_info.get("oa_url") or primary_loc.get("pdf_url") or ""
                doi = item.get("doi") or ""

                papers.append({
                    "id": item.get("id", ""),
                    "title": title,
                    "abstract": abstract,
                    "authors": authors[:5],
                    "year": item.get("publication_year"),
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": item.get("cited_by_count", 0),
                    "source_api": "OpenAlex",
                    "journal": journal_info
                })
    except Exception as e:
        logger.error(f"Error fetching from OpenAlex: {e}")
    return papers


async def fetch_europe_pmc_papers(
    query: str, limit: int = 10, min_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetches peer-reviewed journal papers from Europe PMC API."""
    papers = []
    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    if min_year:
        clean_q += f" FIRST_PDATE:[{min_year}-01-01 TO 2030-12-31]"

    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={clean_q}&format=json&pageSize={limit}"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                logger.warning(f"Europe PMC API returned status {resp.status_code}")
                return papers
            
            data = resp.json()
            results = data.get("resultList", {}).get("result", [])

            for item in results:
                title = item.get("title", "").rstrip(".")
                if not title:
                    continue

                abstract = item.get("abstractText") or ""
                author_str = item.get("authorString") or ""
                authors = [a.strip() for a in author_str.split(",") if a.strip()]

                pub_year = int(item.get("pubYear")) if item.get("pubYear") and item.get("pubYear").isdigit() else None
                journal_title = item.get("journalTitle") or "Indexed Scientific Journal"
                citation_count = int(item.get("citedByCount", 0))

                venue_data = {
                    "name": journal_title,
                    "type": "journal",
                    "cited_by_count": citation_count
                }
                journal_info = evaluate_journal_quality(venue_data)

                doi = f"https://doi.org/{item.get('doi')}" if item.get("doi") else ""
                pdf_url = f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={item.get('pmcid')}&blobtype=pdf" if item.get("pmcid") else ""

                papers.append({
                    "id": item.get("id", ""),
                    "title": title,
                    "abstract": abstract,
                    "authors": authors[:5],
                    "year": pub_year,
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "citation_count": citation_count,
                    "source_api": "Europe PMC",
                    "journal": journal_info
                })
    except Exception as e:
        logger.error(f"Error fetching from Europe PMC: {e}")
    return papers


async def fetch_crossref_papers(
    query: str, limit: int = 10, min_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetches published journal articles from Crossref API."""
    papers = []
    clean_q = re.sub(r"[^\w\s]", "", query).strip().replace(" ", "+")
    url = f"https://api.crossref.org/works?query={clean_q}&rows={limit}"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                logger.warning(f"Crossref API returned status {resp.status_code}")
                return papers

            items = resp.json().get("message", {}).get("items", [])
            for item in items:
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""
                if not title:
                    continue

                # Year
                issued = item.get("issued", {}).get("date-parts", [[]])[0]
                pub_year = issued[0] if issued else None
                if min_year and pub_year and pub_year < min_year:
                    continue

                abstract = item.get("abstract") or ""
                # Strip HTML tags if present in abstract
                abstract = re.sub(r"<[^>]+>", "", abstract)

                authors = []
                for a in item.get("author", []):
                    name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                    if name:
                        authors.append(name)

                container = item.get("container-title", [])
                journal_name = container[0] if container else "Academic Journal"
                citation_count = int(item.get("is-referenced-by-count", 0))

                venue_data = {
                    "name": journal_name,
                    "type": "journal",
                    "publisher": item.get("publisher", ""),
                    "cited_by_count": citation_count
                }
                journal_info = evaluate_journal_quality(venue_data)

                doi = item.get("URL") or (f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else "")

                papers.append({
                    "id": item.get("DOI", ""),
                    "title": title,
                    "abstract": abstract,
                    "authors": authors[:5],
                    "year": pub_year,
                    "doi": doi,
                    "pdf_url": "",
                    "citation_count": citation_count,
                    "source_api": "Crossref",
                    "journal": journal_info
                })
    except Exception as e:
        logger.error(f"Error fetching from Crossref: {e}")
    return papers


async def fetch_arxiv_papers(
    query: str, limit: int = 10, min_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Fetches preprint papers from arXiv API."""
    papers = []
    clean_q = re.sub(r"[^\w\s]", "", query).strip().replace(" ", "+")
    url = f"http://export.arxiv.org/api/query?search_query=all:{clean_q}&start=0&max_results={limit}"

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code != 200:
                logger.warning(f"arXiv API returned status {resp.status_code}")
                return papers

            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                title = re.sub(r"\s+", " ", title_elem.text).strip() if title_elem is not None else ""
                if not title:
                    continue

                published_elem = entry.find("atom:published", ns)
                year = int(published_elem.text[:4]) if published_elem is not None and len(published_elem.text) >= 4 else None
                if min_year and year and year < min_year:
                    continue

                summary_elem = entry.find("atom:summary", ns)
                abstract = re.sub(r"\s+", " ", summary_elem.text).strip() if summary_elem is not None else ""

                authors = [
                    a.find("atom:name", ns).text
                    for a in entry.findall("atom:author", ns)
                    if a.find("atom:name", ns) is not None
                ]

                arxiv_id_elem = entry.find("atom:id", ns)
                arxiv_id = arxiv_id_elem.text if arxiv_id_elem is not None else ""
                
                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.attrib.get("title") == "pdf":
                        pdf_url = link.attrib.get("href", "")
                        break

                venue_data = {"name": "arXiv Preprint", "type": "repository"}
                journal_info = evaluate_journal_quality(venue_data, is_preprint=True)

                papers.append({
                    "id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors[:5],
                    "year": year,
                    "doi": f"https://doi.org/10.48550/arXiv.{arxiv_id.split('/')[-1]}",
                    "pdf_url": pdf_url,
                    "citation_count": 0,
                    "source_api": "arXiv",
                    "journal": journal_info
                })
    except Exception as e:
        logger.error(f"Error fetching from arXiv: {e}")
    return papers


async def search_all_sources(
    query: str,
    limit: int = 15,
    min_year: Optional[int] = None,
    min_citations: int = 0,
    quartiles: Optional[List[str]] = None,
    sources: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Orchestrates paper search across OpenAlex, Europe PMC, Crossref, and arXiv concurrently.
    Deduplicates results and filters by publication year, citations, and journal quartile (Q1, Q2, Q3, Q4).
    """
    if not sources:
        sources = ["europe_pmc", "crossref", "arxiv", "openalex"]

    tasks = []
    if "openalex" in sources:
        tasks.append(fetch_openalex_papers(query, limit=limit, min_year=min_year))
    if "europe_pmc" in sources:
        tasks.append(fetch_europe_pmc_papers(query, limit=limit, min_year=min_year))
    if "crossref" in sources:
        tasks.append(fetch_crossref_papers(query, limit=limit, min_year=min_year))
    if "arxiv" in sources:
        tasks.append(fetch_arxiv_papers(query, limit=limit, min_year=min_year))

    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    combined_papers: List[Dict[str, Any]] = []
    seen_titles = set()
    seen_dois = set()

    for res in results_lists:
        if isinstance(res, Exception):
            logger.error(f"Source fetch task failed: {res}")
            continue
        for paper in res:
            title_norm = _normalize_title(paper["title"])
            doi = paper.get("doi", "").lower().strip()

            # Skip duplicates
            if title_norm in seen_titles or (doi and doi in seen_dois):
                continue

            # Filtering checks
            if min_citations > 0 and paper.get("citation_count", 0) < min_citations:
                continue

            q_rank = paper.get("journal", {}).get("quartile")
            if quartiles and q_rank not in quartiles:
                continue

            if doi:
                seen_dois.add(doi)
            seen_titles.add(title_norm)
            combined_papers.append(paper)

    # Sort by quality quartile (Q1 first), then citation count
    quartile_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "Preprint (Unranked)": 5}
    combined_papers.sort(
        key=lambda p: (
            quartile_order.get(p.get("journal", {}).get("quartile"), 99),
            -p.get("citation_count", 0)
        )
    )

    return combined_papers[:limit]
