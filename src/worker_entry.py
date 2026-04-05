from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import traceback
from datetime import datetime

from .logging_setup import setup_logging
from .models import Paper
from .paper_worker import process_one_paper


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ArxivFilterPro worker entry")
    parser.add_argument("--payload", required=True, help="Task payload json path")
    return parser.parse_args()


def _paper_from_dict(data: dict) -> Paper:
    return Paper(
        arxiv_id=data["arxiv_id"],
        title=data["title"],
        authors=data["authors"],
        abstract=data["abstract"],
        updated=datetime.fromisoformat(data["updated"]),
        published=datetime.fromisoformat(data["published"]),
        categories=data["categories"],
        primary_category=data["primary_category"],
        abs_url=data["abs_url"],
        pdf_url=data["pdf_url"],
    )


def main() -> None:
    args = _parse_args()
    with open(args.payload, "r", encoding="utf-8") as f:
        payload = json.load(f)

    setup_logging(payload["log_level"], payload["run_tag"], payload["worker_log_path"])
    paper = _paper_from_dict(payload["paper"])

    try:
        result = process_one_paper(
            paper,
            output_root=payload["output_root"],
            prompt_template_text=payload["prompt_template_text"],
            codex_cfg=payload["codex_cfg"],
            timezone_name=payload["timezone_name"],
            codex_timeout_sec=int(payload["codex_timeout_sec"]),
            logs_dir=payload["logs_dir"],
            run_tag=payload["run_tag"],
        )
        response = {
            "arxiv_id": result.arxiv_id,
            "success": result.success,
            "error": result.error,
            "paper_dir": result.paper_dir,
            "log_path": result.log_path,
        }
    except Exception:
        logging.exception("Worker crashed for %s", paper.arxiv_id)
        response = {
            "arxiv_id": paper.arxiv_id,
            "success": False,
            "error": (
                f"worker exception; see {payload['worker_log_path']}\n"
                f"{traceback.format_exc()}"
            ),
            "paper_dir": os.path.join(payload["output_root"], paper.arxiv_id),
            "log_path": payload["worker_log_path"],
        }

    sys.stdout.write(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
