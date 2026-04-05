from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from .codex_runner import REQUIRED_MD_FILES, run_codex_once
from .models import Paper, WorkerResult

logger = logging.getLogger(__name__)


def _render_prompt(template_text: str, paper: Paper) -> str:
    return (
        template_text.replace("https://www.arxiv.org/abs/2508.15048", paper.abs_url)
        .replace("{{ARXIV_ABS_URL}}", paper.abs_url)
        .replace("{{ARXIV_ID}}", paper.arxiv_id)
    )


def _has_all_outputs(paper_dir: str) -> bool:
    for name in REQUIRED_MD_FILES:
        path = os.path.join(paper_dir, name)
        if not os.path.exists(path):
            return False
        if os.path.getsize(path) == 0:
            return False
    return True


def _write_metadata(paper_dir: str, paper: Paper, timezone_name: str) -> None:
    today = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    metadata = {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "date": today,
        "abs_url": paper.abs_url,
        "pdf_url": paper.pdf_url,
        "updated_utc": paper.updated.isoformat(),
        "published_utc": paper.published.isoformat(),
        "categories": paper.categories,
        "primary_category": paper.primary_category,
    }
    with open(os.path.join(paper_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def _rotate_existing_paper_dir(paper_dir: str, run_tag: str) -> None:
    if not os.path.exists(paper_dir):
        return

    candidate = f"{paper_dir}__archived_{run_tag}"
    if not os.path.exists(candidate):
        os.rename(paper_dir, candidate)
        logger.info("Archived existing paper dir: %s -> %s", paper_dir, candidate)
        return

    suffix = 1
    while True:
        rotated = f"{candidate}_{suffix}"
        if not os.path.exists(rotated):
            os.rename(paper_dir, rotated)
            logger.info("Archived existing paper dir: %s -> %s", paper_dir, rotated)
            return
        suffix += 1


def _download_pdf(paper_dir: str, paper: Paper) -> str:
    pdf_path = os.path.join(paper_dir, "paper.pdf")
    urllib.request.urlretrieve(paper.pdf_url, pdf_path)
    logger.info("Downloaded PDF for %s to %s", paper.arxiv_id, pdf_path)
    return pdf_path


def _remove_downloaded_pdf(paper_dir: str, arxiv_id: str) -> None:
    pdf_path = os.path.join(paper_dir, "paper.pdf")
    if os.path.isfile(pdf_path):
        os.remove(pdf_path)
        logger.info("Removed PDF for %s", arxiv_id)


def process_one_paper(
    paper: Paper,
    *,
    output_root: str,
    prompt_template_text: str,
    codex_cfg: dict,
    timezone_name: str,
    codex_timeout_sec: int,
    logs_dir: str,
    run_tag: str,
) -> WorkerResult:
    paper_dir = os.path.join(output_root, paper.arxiv_id)
    _rotate_existing_paper_dir(paper_dir, run_tag)
    os.makedirs(paper_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    _write_metadata(paper_dir, paper, timezone_name)
    _download_pdf(paper_dir, paper)
    log_path = os.path.join(logs_dir, f"codex_{paper.arxiv_id}_{run_tag}.txt")

    prompt = _render_prompt(prompt_template_text, paper)
    prompt_path = os.path.join(paper_dir, "codex_prompt.md")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    max_attempts = 1 + int(codex_cfg.get("retries_if_missing_outputs", 1))
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        return_code, error_message = run_codex_once(
            paper_dir=paper_dir,
            prompt=prompt,
            prompt_file=prompt_path,
            paper_id=paper.arxiv_id,
            paper_url=paper.abs_url,
            codex_cfg=codex_cfg,
            timeout_sec=codex_timeout_sec,
            log_path=log_path,
        )

        if return_code == 0 and _has_all_outputs(paper_dir):
            logger.info("Paper %s done in attempt %d", paper.arxiv_id, attempt)
            _remove_downloaded_pdf(paper_dir, paper.arxiv_id)
            return WorkerResult(
                arxiv_id=paper.arxiv_id,
                success=True,
                error="",
                paper_dir=paper_dir,
                log_path=log_path,
            )

        output_state = "missing output files"
        if return_code != 0:
            output_state = f"codex exit code {return_code}"
        if error_message:
            output_state = f"{output_state}; {error_message}"
        last_error = f"{output_state}; see {log_path}"
        logger.warning("Paper %s failed in attempt %d: %s", paper.arxiv_id, attempt, last_error)

    _remove_downloaded_pdf(paper_dir, paper.arxiv_id)
    return WorkerResult(
        arxiv_id=paper.arxiv_id,
        success=False,
        error=last_error,
        paper_dir=paper_dir,
        log_path=log_path,
    )
