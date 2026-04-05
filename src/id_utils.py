import re


VERSIONED_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{5}v\d+$")
BASE_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{5}$")


def ensure_versioned_arxiv_id(arxiv_id: str) -> str:
    value = (arxiv_id or "").strip()
    if not VERSIONED_ARXIV_ID_RE.match(value):
        raise ValueError(f"Invalid arXiv id (must include version): {arxiv_id}")
    return value


def normalize_test_paper_id(arxiv_id: str) -> str:
    value = (arxiv_id or "").strip()
    if VERSIONED_ARXIV_ID_RE.match(value):
        return value
    if BASE_ARXIV_ID_RE.match(value):
        return f"{value}v1"
    raise ValueError(
        f"Invalid test_paper_id: {arxiv_id}. Expected NNNN.NNNNN or NNNN.NNNNNvN."
    )


def extract_arxiv_id_from_entry(entry_id: str) -> str:
    value = entry_id.rstrip("/").split("/")[-1]
    return ensure_versioned_arxiv_id(value)


def version_number(arxiv_id: str) -> int:
    ensure_versioned_arxiv_id(arxiv_id)
    return int(arxiv_id.split("v")[-1])
