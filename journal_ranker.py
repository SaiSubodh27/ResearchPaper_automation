"""
Journal Quality & Quartile Ranking Module

Determines journal name, peer-review status, citation scores (e.g., 2-year mean citedness / Impact Factor estimate),
h-index, and assigns Journal Quality Quartile rankings (Q1, Q2, Q3, Q4) or 'Preprint (Unranked)'.
"""

from typing import Dict, Any, Optional

# High-impact top-tier journals & conferences that default to Q1
TOP_Q1_JOURNALS = {
    "nature", "science", "cell", "the lancet", "pnas", "proceedings of the national academy of sciences",
    "ieee transactions on pattern analysis and machine intelligence", "ieee tpami",
    "journal of machine learning research", "jmlr", "neurips", "nips",
    "advances in neural information processing systems", "icml", "international conference on machine learning",
    "cvpr", "ieee conference on computer vision and pattern recognition", "iccv", "eccv",
    "acl", "association for computational linguistics", "emnlp", "aaai", "ijcai",
    "bioinformatics", "nucleic acids research", "nature communications", "science advances",
    "ieee transactions on knowledge and data engineering", "acm computing surveys"
}

def evaluate_journal_quality(venue: Dict[str, Any], is_preprint: bool = False) -> Dict[str, Any]:
    """
    Evaluates venue metadata and calculates journal quality parameters.

    Args:
        venue: Dictionary containing venue metadata from OpenAlex, Semantic Scholar, etc.
               Expected keys: name, type, 2yr_mean_citedness, h_index, cited_by_count, issn, publisher
        is_preprint: True if paper is explicitly from a preprint server (e.g., arXiv).

    Returns:
        Dictionary with journal_name, is_peer_reviewed, citation_score, h_index, quartile, and quality_tier.
    """
    name = (venue.get("name") or "Unknown Venue").strip()
    name_lower = name.lower()
    venue_type = (venue.get("type") or "").lower()

    # Detect preprints
    if is_preprint or "arxiv" in name_lower or "biorxiv" in name_lower or "medrxiv" in name_lower or venue_type == "repository":
        return {
            "journal_name": name if name != "Unknown Venue" else "arXiv Preprint",
            "is_peer_reviewed": False,
            "citation_score": float(venue.get("2yr_mean_citedness") or 0.0),
            "h_index": int(venue.get("h_index") or 0),
            "quartile": "Preprint (Unranked)",
            "quality_tier": "Preprint",
            "publisher": venue.get("publisher") or "arXiv / Open Repository"
        }

    # Extract metrics
    citation_score = float(venue.get("2yr_mean_citedness") or venue.get("impact_factor") or 0.0)
    h_index = int(venue.get("h_index") or 0)
    cited_by_count = int(venue.get("cited_by_count") or 0)

    # Check for direct top-tier match
    is_top_q1 = False
    for top_j in TOP_Q1_JOURNALS:
        if top_j in {"science", "nature", "cell", "pnas"}:
            if name_lower == top_j or name_lower.startswith(top_j + " ") or name_lower.endswith(" " + top_j):
                # Ensure it's not a generic combination like "Journal of Applied Science"
                if name_lower in {top_j, f"{top_j} journal", f"journal {top_j}"}:
                    is_top_q1 = True
                    break
        else:
            if top_j in name_lower:
                is_top_q1 = True
                break

    # Calculate Quartile based on citation metrics & top-tier list
    if is_top_q1 or citation_score >= 3.5 or h_index >= 80:
        quartile = "Q1"
        quality_tier = "Top-Tier (Q1)"
    elif citation_score >= 2.0 or h_index >= 45 or cited_by_count >= 1000:
        quartile = "Q2"
        quality_tier = "High Quality (Q2)"
    elif citation_score >= 1.0 or h_index >= 20:
        quartile = "Q3"
        quality_tier = "Moderate Quality (Q3)"
    elif citation_score > 0.0 or h_index > 0 or venue_type in ["journal", "conference"]:
        quartile = "Q4"
        quality_tier = "Indexed (Q4)"
    else:
        # Default for peer-reviewed journals without full metric data
        quartile = "Q2" if venue_type in ["journal", "conference"] else "Q3"
        quality_tier = f"Peer-Reviewed ({quartile})"

    return {
        "journal_name": name,
        "is_peer_reviewed": True,
        "citation_score": round(citation_score, 2),
        "h_index": h_index,
        "quartile": quartile,
        "quality_tier": quality_tier,
        "publisher": venue.get("publisher") or "Academic Publisher"
    }
