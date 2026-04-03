from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
import logging
from pathlib import Path
import re
from urllib.parse import urlparse

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument, ParsedSection
from rfp_rag_assistant.parsers.title_normalization import normalize_section_title


@dataclass(slots=True)
class _SectionBuffer:
    title: str
    heading_path: tuple[str, ...]
    parts: list[str] = field(default_factory=list)


class _HTMLSectionExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page_title = ""
        self._in_title = False
        self._ignored_depth = 0
        self._current_tag: str | None = None
        self._text_parts: list[str] = []
        self._sections: list[_SectionBuffer] = []
        self._current_section: _SectionBuffer | None = None
        self._current_heading: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = True
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}:
            self._current_tag = tag
            self._text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "noscript", "svg"}:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag == "title":
            self._in_title = False
            return

        if tag != self._current_tag:
            return

        text = self._clean_text(" ".join(self._text_parts))
        self._current_tag = None
        self._text_parts = []
        if not text:
            return
        if tag.startswith("h"):
            self._start_section(text)
            return
        self._append_to_section(text)

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._in_title:
            self.page_title += data
            return
        if self._current_tag is not None:
            self._text_parts.append(data)

    def sections(self) -> list[_SectionBuffer]:
        return [section for section in self._sections if section.parts]

    def _start_section(self, heading: str) -> None:
        self._current_heading = heading
        self._current_section = _SectionBuffer(title=heading, heading_path=(heading,))
        self._sections.append(self._current_section)

    def _append_to_section(self, text: str) -> None:
        if self._current_section is None:
            title = self._clean_text(self.page_title) or "Page Content"
            self._current_section = _SectionBuffer(title=title, heading_path=(title,))
            self._sections.append(self._current_section)
        self._current_section.parts.append(text)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()


@dataclass(slots=True)
class HTMLReferenceParser:
    document_type: str = "external_reference"
    subtype: str = "html_reference"
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        html = str(document.payload)
        extractor = _HTMLSectionExtractor()
        extractor.feed(html)

        source_url = str(document.metadata.get("source_url", ""))
        source_domain = str(document.metadata.get("source_domain", ""))
        page_title = extractor.page_title.strip() or Path(document.source_file).stem
        sections = self._build_sections(
            document=document,
            page_title=page_title,
            source_url=source_url,
            source_domain=source_domain,
            buffers=extractor.sections(),
        )
        self.logger.info(
            "Parsed HTML reference url=%s domain=%s sections=%s title=%s",
            source_url or "<missing>",
            source_domain or urlparse(source_url).netloc.lower() or "<missing>",
            len(sections),
            page_title,
        )
        return ParsedDocument(
            source_file=document.source_file,
            file_type=document.file_type,
            document_type=self.document_type,
            extracted_at=datetime.now(UTC),
            sections=sections,
            metadata={
                "subtype": self.subtype,
                "source_url": source_url,
                "source_domain": source_domain,
                "reference_origin": document.metadata.get("reference_origin"),
                "referenced_from_file": document.metadata.get("referenced_from_file"),
                "referenced_from_classification": document.metadata.get("referenced_from_classification"),
                "section_count": len(sections),
                "page_title": page_title,
            },
        )

    def _build_sections(
        self,
        *,
        document: LoadedDocument,
        page_title: str,
        source_url: str,
        source_domain: str,
        buffers: list[_SectionBuffer],
    ) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        for index, buffer in enumerate(buffers, start=1):
            text = "\n\n".join(part for part in buffer.parts if part).strip()
            if not text:
                continue
            title = buffer.title or page_title
            if self._is_boilerplate_section(title=title, text=text, page_title=page_title):
                continue
            section_id = self._slugify(f"{title}-{index}")
            sections.append(
                ParsedSection(
                    section_id=section_id,
                    title=title,
                    text=text,
                    kind="reference_content",
                    heading_path=buffer.heading_path,
                    structured_data={
                        "source_format": "html",
                        "page_title": page_title,
                        "section_title_normalized": normalize_section_title(title),
                        "source_url": source_url,
                        "source_domain": source_domain or urlparse(source_url).netloc.lower(),
                        "reference_origin": document.metadata.get("reference_origin"),
                        "referenced_from_file": document.metadata.get("referenced_from_file"),
                        "referenced_from_classification": document.metadata.get("referenced_from_classification"),
                    },
                )
            )
        return sections

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "section"

    def _is_boilerplate_section(self, *, title: str, text: str, page_title: str) -> bool:
        lowered_title = title.lower()
        lowered_text = text.lower()
        boilerplate_phrases = (
            "cookies on",
            "cookie policy",
            "cookie preferences",
            "change my preferences",
            "i'm ok with analytics cookies",
            "accept cookies",
            "skip to main content",
        )
        if any(phrase in lowered_title or phrase in lowered_text for phrase in boilerplate_phrases):
            return True

        lines = [part.strip() for part in text.split("\n\n") if part.strip()]
        if title == page_title and len(lines) >= 12:
            short_lines = [line for line in lines if len(line.split()) <= 4]
            nav_terms = {
                "home",
                "donate",
                "accounts",
                "webcasts",
                "posters",
                "poster presentations",
                "membership benefits",
                "executive committee",
                "education and training resources",
                "external training events",
                "associated papers",
                "submit a news item",
                "published 2025",
                "published 2024",
            }
            nav_hits = sum(1 for line in short_lines if line.lower() in nav_terms)
            if len(short_lines) >= max(8, len(lines) // 2) or nav_hits >= 4:
                return True

        generic_listing_titles = {
            "journal",
            "journals",
            "news",
            "resources",
            "guidance",
            "articles",
            "latest",
        }
        if lowered_title in generic_listing_titles and len(lines) <= 6:
            if sum(1 for line in lines if len(line.split()) <= 6) >= max(2, len(lines) - 1):
                return True

        listing_markers = {
            "guidance",
            "published 2025",
            "published 2024",
            "associated papers",
            "external training events",
            "pmg journal",
        }
        if len(lines) <= 8 and sum(1 for line in lines if line.lower() in listing_markers) >= 2:
            return True

        promotional_title_markers = (
            "conference",
            "exhibition",
            "training",
            "webinar",
            "agm",
            "recordings",
        )
        promotional_text_markers = (
            "our annual event provides",
            "networking opportunities",
            "register now",
            "book your place",
            "sponsorship",
            "industry exhibition",
        )
        if any(marker in lowered_title for marker in promotional_title_markers):
            return True
        if any(marker in lowered_text for marker in promotional_text_markers):
            return True

        return False
