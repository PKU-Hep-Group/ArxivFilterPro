from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import arxiv

from .id_utils import ensure_versioned_arxiv_id, extract_arxiv_id_from_entry
from .models import Paper

logger = logging.getLogger(__name__)


def _to_paper(result: arxiv.Result) -> Paper:
    arxiv_id = extract_arxiv_id_from_entry(result.entry_id)
    ensure_versioned_arxiv_id(arxiv_id)
    return Paper(
        arxiv_id=arxiv_id,
        title=result.title.strip(),
        authors=[author.name for author in result.authors],
        abstract=result.summary.replace("\n", " ").strip(),
        updated=result.updated,
        published=result.published,
        categories=result.categories,
        primary_category=result.primary_category,
        abs_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=result.pdf_url,
    )


def fetch_recent_by_categories(
    categories: list[str],
    max_results_per_category: int,
    lookback_hours: int = 24,
) -> list[Paper]:
    now_utc = datetime.now(timezone.utc)
    lower = now_utc - timedelta(hours=lookback_hours)
    dedup: dict[str, Paper] = {}

    for category in categories:
        query = f"cat:{category}"
        search = arxiv.Search(
            query=query,
            sort_by=arxiv.SortCriterion.LastUpdatedDate,
            max_results=max_results_per_category,
        )
        count = 0
        for result in search.results():
            try:
                paper = _to_paper(result)
            except ValueError as e:
                logger.warning("Skip invalid paper id from entry %s: %s", result.entry_id, e)
                continue
            if not (lower <= paper.updated <= now_utc):
                continue
            dedup[paper.arxiv_id] = paper
            count += 1
        logger.info("Category %s recent papers in 24h: %d", category, count)

    papers = sorted(
        dedup.values(),
        key=lambda p: p.updated,
        reverse=True,
    )
    logger.info("Total recent unique papers: %d", len(papers))
    return papers


def fetch_paper_by_id(arxiv_id_with_version: str) -> Paper:
    ensure_versioned_arxiv_id(arxiv_id_with_version)
    search = arxiv.Search(id_list=[arxiv_id_with_version], max_results=1)
    results = list(search.results())
    if not results:
        raise ValueError(f"No arXiv result found for {arxiv_id_with_version}")
    paper = _to_paper(results[0])
    if paper.arxiv_id != arxiv_id_with_version:
        raise ValueError(
            f"Requested {arxiv_id_with_version}, but arXiv returned {paper.arxiv_id}"
        )
    return paper
