from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .base import LoadedDocument


def _default_fetch_html(url: str, *, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


@dataclass(slots=True)
class ExternalReferenceLoader:
    fetch_html: Callable[[str], str] | None = None
    user_agent: str = "Mozilla/5.0"

    def load_url(
        self,
        url: str,
        *,
        reference_origin: str = "customer_cited",
        referenced_from_file: Path | None = None,
        referenced_from_classification: str | None = None,
    ) -> LoadedDocument:
        html = (
            self.fetch_html(url)
            if self.fetch_html is not None
            else _default_fetch_html(url, user_agent=self.user_agent)
        )
        parsed = urlparse(url)
        source_file = self._build_virtual_source_file(parsed)

        return LoadedDocument(
            source_file=source_file,
            file_type="html",
            payload=html,
            metadata={
                "source_url": url,
                "source_domain": parsed.netloc.lower(),
                "reference_origin": reference_origin,
                "referenced_from_file": str(referenced_from_file) if referenced_from_file else None,
                "referenced_from_classification": referenced_from_classification,
            },
        )

    def _build_virtual_source_file(self, parsed_url: object) -> Path:
        parsed = parsed_url
        path = getattr(parsed, "path", "") or "/"
        clean_path = re.sub(r"/{2,}", "/", path).strip("/")
        clean_path = re.sub(r"[^A-Za-z0-9/_-]", "-", clean_path)
        if not clean_path:
            clean_path = "index"
        if not clean_path.endswith(".html"):
            clean_path = f"{clean_path}.html"
        return Path("external_reference") / getattr(parsed, "netloc", "unknown") / clean_path
