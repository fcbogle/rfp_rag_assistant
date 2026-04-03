from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from pathlib import Path
import re

from pypdf import PdfReader

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument, ParsedSection
from rfp_rag_assistant.parsers.title_normalization import normalize_section_title


@dataclass(slots=True)
class PDFSectionParser:
    document_type: str
    subtype: str
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        if isinstance(document.payload, (str, Path)):
            return self.parse_file(Path(document.payload))
        return self.parse_file(document.source_file)

    def parse_file(self, source_file: Path) -> ParsedDocument:
        page_lines = self._extract_page_lines(source_file)
        content_lines = self._filter_repeated_headers_and_footers(page_lines)
        sections = self._cleanup_sections(self._build_sections(source_file, content_lines))
        self.logger.info(
            "Parsed PDF file=%s subtype=%s pages=%s content_lines=%s sections=%s",
            source_file.name,
            self.subtype,
            len(page_lines),
            len(content_lines),
            len(sections),
        )

        return ParsedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            document_type=self.document_type,
            extracted_at=datetime.now(UTC),
            sections=sections,
            metadata={
                "subtype": self.subtype,
                "page_count": len(page_lines),
                "section_count": len(sections),
            },
        )

    def _cleanup_sections(self, sections: list[ParsedSection]) -> list[ParsedSection]:
        if not sections:
            return sections

        cleaned: list[ParsedSection] = []
        for section in sections:
            if cleaned and self._should_merge_into_previous(section, cleaned[-1]):
                previous = cleaned[-1]
                merged_text = "\n\n".join(part for part in (previous.text, section.title, section.text) if part).strip()
                cleaned[-1] = ParsedSection(
                    section_id=previous.section_id,
                    title=previous.title,
                    text=merged_text,
                    kind=previous.kind,
                    heading_path=previous.heading_path,
                    structured_data=previous.structured_data,
                )
                continue
            cleaned.append(section)

        return cleaned

    def _extract_page_lines(self, source_file: Path) -> list[list[str]]:
        reader = PdfReader(str(source_file))
        pages: list[list[str]] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            lines = []
            for raw in text.splitlines():
                line = " ".join(raw.split()).strip()
                if line:
                    lines.append(line)
            pages.append(lines)
        return pages

    def _filter_repeated_headers_and_footers(self, page_lines: list[list[str]]) -> list[str]:
        candidate_counter: Counter[str] = Counter()
        for lines in page_lines:
            for line in lines[:6] + lines[-6:]:
                if line:
                    candidate_counter[line] += 1

        repeated = {
            line
            for line, count in candidate_counter.items()
            if count >= 2 and (
                self._is_repeated_page_artifact(line)
                or (count >= 3 and self._looks_like_repeated_running_header(line))
            )
        }

        content: list[str] = []
        for lines in page_lines:
            for index, line in enumerate(lines):
                if line in repeated and (index < 6 or index >= len(lines) - 6):
                    continue
                content.append(line)
        return content

    def _is_repeated_page_artifact(self, line: str) -> bool:
        compact = line.strip()
        if not compact:
            return False
        if re.fullmatch(r"\d+", compact):
            return True
        if re.search(r"\bpage\s+\d+\b", compact, flags=re.IGNORECASE):
            return True
        if "issue:" in compact.lower() or "template:" in compact.lower():
            return True
        if "authority's reference number" in compact.lower():
            return True
        if "framework reference number" in compact.lower():
            return True
        return False

    def _looks_like_repeated_running_header(self, line: str) -> bool:
        compact = line.strip()
        if not compact or len(compact) > 90:
            return False
        if re.match(r"^\d+(\.\d+)*\s+", compact):
            return False
        words = compact.split()
        if len(words) > 10:
            return False
        if compact.lower() in {"contents", "table of contents"}:
            return False
        capitalised = sum(1 for word in words if word[:1].isupper())
        return capitalised / max(1, len(words)) >= 0.6

    def _build_sections(self, source_file: Path, lines: list[str]) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        heading_stack: list[str] = []
        current_title = source_file.stem
        current_parts: list[str] = []
        section_counter = 0

        for line in lines:
            if self._looks_like_toc_entry(line):
                continue
            if self._is_heading(line):
                self._flush_section(
                    sections=sections,
                    source_file=source_file,
                    current_title=current_title,
                    current_parts=current_parts,
                    heading_stack=heading_stack,
                    section_counter=section_counter,
                )
                if current_parts:
                    section_counter += 1
                    current_parts = []
                heading_stack = self._resolve_heading_path(heading_stack, line)
                current_title = line
                continue
            current_parts.append(line)

        self._flush_section(
            sections=sections,
            source_file=source_file,
            current_title=current_title,
            current_parts=current_parts,
            heading_stack=heading_stack,
            section_counter=section_counter,
        )
        return sections

    def _flush_section(
        self,
        *,
        sections: list[ParsedSection],
        source_file: Path,
        current_title: str,
        current_parts: list[str],
        heading_stack: list[str],
        section_counter: int,
    ) -> None:
        text = "\n\n".join(part.strip() for part in current_parts if part.strip()).strip()
        if not text:
            return
        section_id = self._slugify(current_title or source_file.stem or f"section-{section_counter + 1}")
        normalized_title = normalize_section_title(current_title or source_file.stem)
        sections.append(
            ParsedSection(
                section_id=section_id,
                title=current_title or source_file.stem,
                text=text,
                kind="reference_content",
                heading_path=tuple(heading_stack) if heading_stack else ((current_title,) if current_title else ()),
                structured_data={
                    "source_format": "pdf",
                    "section_title_normalized": normalized_title,
                },
            )
        )

    def _is_heading(self, line: str) -> bool:
        text = line.strip()
        if not text or len(text) > 180:
            return False
        if self._looks_like_toc_entry(text):
            return False
        if self._looks_like_address_or_fragment(text):
            return False
        if re.match(r"^(section|annex)\s+[a-z0-9]", text, flags=re.IGNORECASE):
            return True
        if re.match(r"^\d+(\.\d+)*\s+[A-Z].+", text):
            return True
        if text.isupper() and len(text.split()) <= 12:
            return True
        title_case_words = text.split()
        if 1 < len(title_case_words) <= 10 and not text.endswith("."):
            capped = sum(1 for word in title_case_words if word[:1].isupper())
            if capped / len(title_case_words) >= 0.7:
                return True
        return False

    def _looks_like_address_or_fragment(self, line: str) -> bool:
        text = line.strip()
        if re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}", text, flags=re.IGNORECASE):
            return True
        if re.fullmatch(r"[A-Z]\.", text):
            return True
        if re.fullmatch(r"\d{1,3}[A-Z]?", text):
            return True

        words = text.split()
        if len(words) <= 3:
            address_terms = {
                "street",
                "st",
                "road",
                "rd",
                "avenue",
                "ave",
                "close",
                "lane",
                "ln",
                "drive",
                "dr",
                "way",
                "place",
                "pl",
                "grove",
                "court",
                "ct",
            }
            lowered = {word.rstrip(".,").lower() for word in words}
            if lowered & address_terms:
                return True
        return False

    def _should_merge_into_previous(self, section: ParsedSection, previous: ParsedSection) -> bool:
        title = section.title.strip()
        text = section.text.strip()
        combined = " ".join(part for part in (title, text) if part).strip()

        if self._looks_like_address_heading(title):
            return True
        if self._looks_like_admin_label(title):
            return True
        if self._looks_like_response_status_heading(title):
            return True
        if self._looks_like_tender_table_row_heading(title=title, text=text, previous_title=previous.title):
            return True
        if len(combined) <= 120 and self._looks_like_address_or_fragment(title):
            return True
        return False

    def _looks_like_address_heading(self, title: str) -> bool:
        text = title.strip()
        if not text:
            return False
        if re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}", text, flags=re.IGNORECASE):
            return True

        county_or_city = {
            "east sussex",
            "west sussex",
            "brighton",
            "brighton and hove",
            "sussex",
        }
        if text.lower() in county_or_city:
            return True

        if len(text.split()) <= 4 and any(
            token in text.lower()
            for token in ("hospital", "road", "street", "avenue", "grove", "lane", "drive", "court")
        ):
            return True
        return False

    def _looks_like_admin_label(self, title: str) -> bool:
        text = title.strip().lower()
        return text in {
            "document name action",
            "event date",
            "form draft",
            "no response required – for information",
            "no response required - for information",
            "cover letter",
            "response document",
            "commercially sensitive information",
        }

    def _looks_like_response_status_heading(self, title: str) -> bool:
        text = title.strip()
        lowered = text.lower()
        if "no response required" in lowered:
            return True
        if text.startswith("Completed Annex "):
            return True
        if re.fullmatch(r"\d{2}\.\s+.+", text):
            return True
        if text.endswith("Form DRAFT"):
            return True
        return False

    def _looks_like_tender_table_row_heading(self, *, title: str, text: str, previous_title: str) -> bool:
        if self.document_type != "tender_details":
            return False

        lowered_title = title.strip().lower()
        lowered_previous = previous_title.strip().lower()
        combined = " ".join(part for part in (title, text) if part).strip()

        parent_like_sections = {
            "overview of tender documentation",
            "tender timetable",
            "tender evaluation methodology and criteria",
        }
        if lowered_previous not in parent_like_sections:
            return False

        if re.match(r"^\d+(\.\d+)*\s+", title):
            return False
        if re.match(r"^(section|annex)\s+", title, flags=re.IGNORECASE):
            return False
        if title.isupper():
            return False

        table_label_prefixes = (
            "the ",
            "completed ",
            "commercially sensitive",
            "clarification ",
            "cover letter",
            "response document",
            "event ",
            "criteria ",
            "total ",
        )
        if lowered_title.startswith(table_label_prefixes):
            return True

        if len(title.split()) <= 6 and len(combined) <= 220:
            return True

        return False

    def _looks_like_toc_entry(self, line: str) -> bool:
        if "...." in line:
            return True
        if re.search(r"\.{3,}\s*\d+\s*$", line):
            return True
        if re.match(r"^[A-Z][A-Z\s&/-]+\d+\s*$", line):
            return True
        return False

    def _resolve_heading_path(self, heading_stack: list[str], title: str) -> list[str]:
        level = self._heading_level(title)
        base = heading_stack[: level - 1]
        base.append(title)
        return base

    def _heading_level(self, title: str) -> int:
        match = re.match(r"^(\d+(?:\.\d+)*)\s+", title)
        if match:
            return max(1, len(match.group(1).split(".")))
        if re.match(r"^(section|annex)\s+[a-z0-9]", title, flags=re.IGNORECASE):
            return 1
        return 1

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "section"
