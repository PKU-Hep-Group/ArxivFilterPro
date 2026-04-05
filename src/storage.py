from __future__ import annotations

import csv
import os

from .id_utils import ensure_versioned_arxiv_id


def load_previous_ids(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()

    valid: set[str] = set()
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            arxiv_id = (row.get("arxiv_id") or "").strip()
            if not arxiv_id:
                continue
            valid.add(ensure_versioned_arxiv_id(arxiv_id))
    return valid


def append_previous_ids(path: str, ids: set[str], run_tag: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sorted_ids = sorted(ensure_versioned_arxiv_id(v) for v in ids)
    file_exists = os.path.exists(path)

    with open(path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "arxiv_id"])
        for arxiv_id in sorted_ids:
            writer.writerow([run_tag, arxiv_id])
