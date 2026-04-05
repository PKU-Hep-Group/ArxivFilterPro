from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    updated: datetime
    published: datetime
    categories: list[str]
    primary_category: str
    abs_url: str
    pdf_url: str

    @property
    def content_text(self) -> str:
        return "\n".join(
            [
                self.title,
                ", ".join(self.authors),
                ", ".join(self.categories),
                self.abstract,
                self.abs_url,
                self.pdf_url,
                self.arxiv_id,
            ]
        )

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["updated"] = self.updated.isoformat()
        payload["published"] = self.published.isoformat()
        return payload


@dataclass
class WorkerResult:
    arxiv_id: str
    success: bool
    error: str
    paper_dir: str
    log_path: str
