from __future__ import annotations

import os
from typing import Any

import yaml


def _required(config: dict[str, Any], key: str) -> Any:
    if key not in config:
        raise ValueError(f"Missing required config key: {key}")
    return config[key]


def load_config(config_path: str) -> dict[str, Any]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"{config_path} not found. Copy config_template.yaml to config.yaml first."
        )
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    _required(config, "categories")
    _required(config, "keyword_logic")
    _required(config, "runtime")
    _required(config, "test_mode")
    _required(config, "sites")
    _required(config, "mail")
    _required(config, "codex")

    runtime = config["runtime"]
    runtime.setdefault("timezone", "UTC")
    runtime.setdefault("max_results_per_category", 300)
    runtime.setdefault("lookback_hours", 24)
    runtime.setdefault("max_workers", 2)
    runtime.setdefault("log_level", "INFO")
    runtime.setdefault("prompt_template", "prompts/paper_summary_prompt.md")
    runtime.setdefault("output_root", "data")
    runtime.setdefault("previous_arxivs_file", "previous_arxivs.csv")
    runtime.setdefault("codex_timeout_sec", 1800)
    runtime.setdefault("logs_dir", "logs")

    test_mode = config["test_mode"]
    test_mode.setdefault("enabled", False)
    test_mode.setdefault("test_paper_id", "")
    test_mode.setdefault("skip_site_commit", False)
    test_mode.setdefault("dummy_codex", False)

    sites = config["sites"]
    _required(sites, "local_path")
    _required(sites, "public_url")
    sites.setdefault("branch", "main")
    sites.setdefault("auto_push", True)
    sites.setdefault("commit_message_template", "Daily update: {date}")
    sites.setdefault("cards_data_relpath", "data/cards.json")

    mail = config["mail"]
    _required(mail, "host")
    _required(mail, "user")
    _required(mail, "password")
    _required(mail, "receiver")
    mail.setdefault("port", 465)
    mail.setdefault("dryrun", True)

    codex_cfg = config["codex"]
    codex_cfg.setdefault(
        "command_template",
        [
            "codex",
            "exec",
            "--full-auto",
            "--skip-git-repo-check",
            "{prompt}",
        ],
    )
    codex_cfg.setdefault("retries_if_missing_outputs", 1)
    codex_cfg.setdefault("shell", "/bin/zsh")
    codex_cfg.setdefault("shell_rcfile", "")
    codex_cfg.setdefault("pre_command", "")

    return config
