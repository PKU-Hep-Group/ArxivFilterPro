from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def _run_git(site_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git"] + args,
        cwd=site_path,
        text=True,
        capture_output=True,
        check=False,
    )


def commit_and_push_site(
    *,
    site_path: str,
    branch: str,
    auto_push: bool,
    commit_message: str,
) -> None:
    if not os.path.exists(os.path.join(site_path, ".git")):
        logger.warning("Skip site git commit: %s is not a git repo", site_path)
        return

    _run_git(site_path, ["checkout", branch])
    _run_git(site_path, ["add", "-A"])
    diff = _run_git(site_path, ["diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        logger.info("No site changes to commit.")
        return

    commit = _run_git(site_path, ["commit", "-m", commit_message])
    if commit.returncode != 0:
        logger.error("Site git commit failed: %s", commit.stderr.strip())
        return
    logger.info("Site committed: %s", commit_message)

    if auto_push:
        push = _run_git(site_path, ["push", "origin", branch])
        if push.returncode != 0:
            logger.error("Site git push failed: %s", push.stderr.strip())
        else:
            logger.info("Site pushed to origin/%s", branch)
