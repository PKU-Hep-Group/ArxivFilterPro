from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import arxiv

from .id_utils import ensure_versioned_arxiv_id, extract_arxiv_id_from_entry
from .models import Paper

logger = logging.getLogger(__name__)

ARXIV_SEARCH_MAX_ATTEMPTS = 10
ARXIV_SEARCH_RETRY_SLEEP_SECONDS = 600


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


def _run_search_with_retries(search: arxiv.Search) -> list[arxiv.Result]:
    last_error: Exception | None = None
    for attempt in range(1, ARXIV_SEARCH_MAX_ATTEMPTS + 1):
        try:
            return list(search.results())
        except Exception as exc:
            last_error = exc
            logger.exception(
                "arXiv search failed on attempt %d/%d",
                attempt,
                ARXIV_SEARCH_MAX_ATTEMPTS,
            )
            if attempt >= ARXIV_SEARCH_MAX_ATTEMPTS:
                break
            logger.warning(
                "Retrying arXiv search in %d seconds",
                ARXIV_SEARCH_RETRY_SLEEP_SECONDS,
            )
            time.sleep(ARXIV_SEARCH_RETRY_SLEEP_SECONDS)

    assert last_error is not None
    raise RuntimeError(
        f"arXiv search failed after {ARXIV_SEARCH_MAX_ATTEMPTS} attempts"
    ) from last_error


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
        for result in _run_search_with_retries(search):
            try:
                paper = _to_paper(result)
            except ValueError as e:
                logger.warning("Skip invalid paper id from entry %s: %s", result.entry_id, e)
                continue
            if not (lower <= paper.updated <= now_utc):
                continue
            dedup[paper.arxiv_id] = paper
            count += 1
        logger.info("Category %s recent papers: %d", category, count)

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
    results = _run_search_with_retries(search)
    if not results:
        raise ValueError(f"No arXiv result found for {arxiv_id_with_version}")
    paper = _to_paper(results[0])
    if paper.arxiv_id != arxiv_id_with_version:
        raise ValueError(
            f"Requested {arxiv_id_with_version}, but arXiv returned {paper.arxiv_id}"
        )
    return paper
