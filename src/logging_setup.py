import logging
import os
from datetime import datetime


def make_run_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def setup_logging(log_level: str, run_tag: str, log_path: str | None = None) -> str:
    os.makedirs("logs", exist_ok=True)
    if log_path is None:
        log_path = os.path.join("logs", f"run_{run_tag}.log")
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=True,
    )
    return log_path
