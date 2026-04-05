from __future__ import annotations

import logging
import os
import shlex
import subprocess
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_MD_FILES = [
    "title_zh.md",
    "abstract.md",
    "ai_abstract.md",
    "content.md",
    "keypoint.md",
    "method.md",
    "problem.md",
    "result.md",
]


def _render_command(template: Sequence[str], mapping: dict[str, str]) -> list[str]:
    return [part.format(**mapping) for part in template]


def _build_shell_command(
    command: Sequence[str],
    *,
    shell_rcfile: str,
    pre_command: str,
) -> str:
    parts: list[str] = []
    if shell_rcfile:
        parts.append(f"source {shlex.quote(shell_rcfile)}")
    if pre_command:
        parts.append(pre_command)
    parts.append(shlex.join(command))
    return " && ".join(parts)


def _write_dummy_outputs(paper_dir: str) -> None:
    for name in REQUIRED_MD_FILES:
        path = os.path.join(paper_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("Dummy content\n")


def run_codex_once(
    *,
    paper_dir: str,
    prompt: str,
    prompt_file: str,
    paper_id: str,
    paper_url: str,
    codex_cfg: dict[str, Any],
    timeout_sec: int,
    log_path: str,
) -> tuple[int, str]:
    if codex_cfg.get("dummy_mode", False):
        logger.info("Dummy codex mode enabled for %s", paper_id)
        _write_dummy_outputs(paper_dir)
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n===== dummy codex run for {paper_id} =====\n")
            log_file.write(f"cwd: {paper_dir}\n")
            log_file.write("dummy_mode: true\n")
            log_file.write("generated files:\n")
            for name in REQUIRED_MD_FILES:
                log_file.write(f"- {name}\n")
            log_file.write("\n")
        return 0, ""

    cmd_template = codex_cfg["command_template"]
    command = _render_command(
        cmd_template,
        {
            "prompt": prompt,
            "prompt_file": prompt_file,
            "paper_id": paper_id,
            "paper_url": paper_url,
            "paper_dir": paper_dir,
        },
    )

    shell = codex_cfg.get("shell", "/bin/zsh")
    shell_rcfile = codex_cfg.get("shell_rcfile", "")
    pre_command = codex_cfg.get("pre_command", "")
    shell_command = _build_shell_command(
        command,
        shell_rcfile=shell_rcfile,
        pre_command=pre_command,
    )

    logger.info("Running codex for %s", paper_id)
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"\n===== codex run for {paper_id} =====\n")
        log_file.write(f"cwd: {paper_dir}\n")
        log_file.write(f"command: {shell_command}\n\n")
        log_file.flush()
        process = subprocess.Popen(
            [shell, "-ic", shell_command],
            cwd=paper_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            return_code = process.wait(timeout=timeout_sec)
            return return_code, ""
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            message = f"codex timed out after {timeout_sec} seconds"
            log_file.write(f"\n{message}\n")
            log_file.flush()
            return 124, message
