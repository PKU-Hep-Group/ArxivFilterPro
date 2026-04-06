from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .arxiv_client import fetch_paper_by_id, fetch_recent_by_categories
from .config import load_config
from .id_utils import normalize_test_paper_id
from .keyword_filter import matches_keyword_logic
from .logging_setup import make_run_tag, setup_logging
from .mailer import send_daily_digest
from .models import WorkerResult
from .site_builder import update_cards
from .site_git import commit_and_push_site
from .storage import append_previous_ids, load_previous_ids

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ArxivFilterPro daily runner")
    parser.add_argument("--config", default="config.yaml", help="Path to config yaml")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    return parser.parse_args()


def _filter_papers_by_keyword(papers, keyword_logic: str):
    matched = [p for p in papers if matches_keyword_logic(p.content_text, keyword_logic)]
    logger.info("Keyword matched papers: %d", len(matched))
    return matched


def _write_worker_payload(
    *,
    paper,
    output_root: str,
    prompt_template_text: str,
    codex_cfg: dict,
    timezone_name: str,
    codex_timeout_sec: int,
    logs_dir: str,
    run_tag: str,
    log_level: str,
) -> str:
    worker_log_path = os.path.join(logs_dir, f"worker_{paper.arxiv_id}_{run_tag}.log")
    fd, payload_path = tempfile.mkstemp(
        prefix=f"worker_{paper.arxiv_id}_{run_tag}_",
        suffix=".json",
        dir=logs_dir,
        text=True,
    )
    payload = {
        "paper": paper.to_json_dict(),
        "output_root": output_root,
        "prompt_template_text": prompt_template_text,
        "codex_cfg": codex_cfg,
        "timezone_name": timezone_name,
        "codex_timeout_sec": codex_timeout_sec,
        "logs_dir": logs_dir,
        "run_tag": run_tag,
        "worker_log_path": worker_log_path,
        "log_level": log_level,
    }
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return payload_path


def _terminate_process_group(process: subprocess.Popen[str], force: bool) -> None:
    if process.poll() is not None:
        return
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return


def _run_workers_subprocesses(
    *,
    papers,
    output_root: str,
    prompt_template_text: str,
    codex_cfg: dict,
    timezone_name: str,
    codex_timeout_sec: int,
    logs_dir: str,
    run_tag: str,
    max_workers: int,
    log_level: str,
) -> list[WorkerResult]:
    python_executable = os.environ.get("PYTHON_EXECUTABLE") or os.sys.executable
    queue = list(papers)
    running: dict[subprocess.Popen[str], tuple[str, str, str]] = {}
    results: list[WorkerResult] = []

    try:
        while queue or running:
            while queue and len(running) < max_workers:
                paper = queue.pop(0)
                payload_path = _write_worker_payload(
                    paper=paper,
                    output_root=output_root,
                    prompt_template_text=prompt_template_text,
                    codex_cfg=codex_cfg,
                    timezone_name=timezone_name,
                    codex_timeout_sec=codex_timeout_sec,
                    logs_dir=logs_dir,
                    run_tag=run_tag,
                    log_level=log_level,
                )
                process = subprocess.Popen(
                    [python_executable, "-m", "src.worker_entry", "--payload", payload_path],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                worker_log_path = os.path.join(logs_dir, f"worker_{paper.arxiv_id}_{run_tag}.log")
                running[process] = (paper.arxiv_id, payload_path, worker_log_path)
                logger.info("Started worker for %s (pid=%s)", paper.arxiv_id, process.pid)

            finished: list[subprocess.Popen[str]] = []
            for process, (paper_id, payload_path, worker_log_path) in list(running.items()):
                if process.poll() is None:
                    continue

                stdout, stderr = process.communicate()
                try:
                    os.remove(payload_path)
                except FileNotFoundError:
                    pass

                if stdout.strip():
                    try:
                        payload = json.loads(stdout)
                    except json.JSONDecodeError:
                        result = WorkerResult(
                            arxiv_id=paper_id,
                            success=False,
                            error=(
                                f"worker returned invalid JSON; see {worker_log_path}\n"
                                f"stdout:\n{stdout}\n"
                                f"stderr:\n{stderr}"
                            ).strip(),
                            paper_dir=os.path.join(output_root, paper_id),
                            log_path=worker_log_path,
                        )
                    else:
                        result = WorkerResult(
                            arxiv_id=payload["arxiv_id"],
                            success=payload["success"],
                            error=payload["error"],
                            paper_dir=payload["paper_dir"],
                            log_path=payload["log_path"],
                        )
                else:
                    result = WorkerResult(
                        arxiv_id=paper_id,
                        success=False,
                        error=(
                            stderr
                            or stdout
                            or f"worker exit code {process.returncode}; see {worker_log_path}"
                        ).strip(),
                        paper_dir=os.path.join(output_root, paper_id),
                        log_path=os.path.join(logs_dir, f"codex_{paper_id}_{run_tag}.txt"),
                    )

                results.append(result)
                if result.success:
                    logger.info("Processed %s", result.arxiv_id)
                else:
                    logger.error("Failed %s: %s", result.arxiv_id, result.error)
                    logger.error("Worker log for %s: %s", result.arxiv_id, worker_log_path)
                finished.append(process)

            for process in finished:
                running.pop(process, None)

            if running:
                time.sleep(0.3)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received. Terminating workers and codex subprocesses.")
        for process in list(running):
            _terminate_process_group(process, force=False)
        time.sleep(1.0)
        for process in list(running):
            _terminate_process_group(process, force=True)
        raise
    finally:
        for _, payload_path, _ in running.values():
            try:
                os.remove(payload_path)
            except FileNotFoundError:
                pass

    return results


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    if args.test_mode:
        config["test_mode"]["enabled"] = True
    if config["test_mode"]["enabled"] and config["test_mode"].get("dummy_codex", False):
        config["codex"]["dummy_mode"] = True
    run_tag = make_run_tag()
    setup_logging(config["runtime"]["log_level"], run_tag)
    logger.info("ArxivFilterPro started")

    timezone_name = config["runtime"]["timezone"]
    output_root = config["runtime"]["output_root"]
    prev_file = config["runtime"]["previous_arxivs_file"]
    logs_dir = config["runtime"]["logs_dir"]
    os.makedirs(output_root, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    test_mode = bool(config["test_mode"]["enabled"])
    if test_mode:
        test_id = normalize_test_paper_id(config["test_mode"]["test_paper_id"])
        candidates = [fetch_paper_by_id(test_id)]
        logger.info("Test mode enabled, target paper: %s", test_id)
    else:
        candidates = fetch_recent_by_categories(
            categories=config["categories"],
            max_results_per_category=int(config["runtime"]["max_results_per_category"]),
            lookback_hours=int(config["runtime"]["lookback_hours"]),
        )
        candidates = _filter_papers_by_keyword(candidates, config["keyword_logic"])

    previous_ids = load_previous_ids(prev_file)
    new_papers = [paper for paper in candidates if paper.arxiv_id not in previous_ids]
    logger.info("New papers to process: %d", len(new_papers))

    if not new_papers and not test_mode:
        logger.info("No new matched papers today. Sending daily email and exiting pipeline.")

    with open(config["runtime"]["prompt_template"], "r", encoding="utf-8") as f:
        prompt_template_text = f.read()

    worker_results: list[WorkerResult] = []
    if new_papers:
        worker_results = _run_workers_subprocesses(
            papers=new_papers,
            output_root=output_root,
            prompt_template_text=prompt_template_text,
            codex_cfg=config["codex"],
            timezone_name=timezone_name,
            codex_timeout_sec=int(config["runtime"]["codex_timeout_sec"]),
            logs_dir=logs_dir,
            run_tag=run_tag,
            max_workers=max(1, int(config["runtime"]["max_workers"])),
            log_level=config["runtime"]["log_level"],
        )

    successful_dirs = [r.paper_dir for r in worker_results if r.success]
    site_cfg = config["sites"]
    updated_cards = update_cards(
        site_path=site_cfg["local_path"],
        cards_json_relpath=site_cfg["cards_data_relpath"],
        successful_paper_dirs=successful_dirs,
    )
    logger.info("Updated cards count: %d", len(updated_cards))

    published_ids = {card["id"] for card in updated_cards}
    if not test_mode:
        if published_ids:
            append_previous_ids(prev_file, published_ids, run_tag)

            skip_site_commit = bool(config["test_mode"].get("skip_site_commit", False))
            if (not test_mode) or (not skip_site_commit):
                today = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
                commit_message = site_cfg["commit_message_template"].format(date=today)
                commit_and_push_site(
                    site_path=site_cfg["local_path"],
                    branch=site_cfg["branch"],
                    auto_push=bool(site_cfg["auto_push"]),
                    commit_message=commit_message,
                )
            else:
                logger.info("Skip site commit due to test mode config.")

            send_daily_digest(updated_cards, config["mail"], site_cfg["public_url"])
        else:
            logger.info("No new matched papers today. Skip site commit and daily email.")

    logger.info("ArxivFilterPro finished.")


if __name__ == "__main__":
    main()
