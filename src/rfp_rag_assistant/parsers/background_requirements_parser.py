from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument, ParsedSection
from rfp_rag_assistant.parsers.title_normalization import normalize_section_title

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(slots=True)
class BackgroundRequirementsParser:
    document_type: str = "background_requirements"

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        if isinstance(document.payload, (str, Path)):
            return self.parse_file(Path(document.payload))
        return self.parse_file(document.source_file)

    def parse_file(self, source_file: Path) -> ParsedDocument:
        with ZipFile(source_file) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))

        body = root.find(".//w:body", WORD_NS)
        if body is None:
            raise ValueError(f"Could not find Word document body in {source_file}")

        sections: list[ParsedSection] = []
        heading_stack: list[str] = []
        current_title = source_file.stem
        current_kind = "reference_content"
        current_parts: list[str] = []
        section_counter = 0

        for element in body:
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "p":
                paragraph = self._paragraph_data(element)
                text = paragraph["text"]
                if not text:
                    continue

                if self._is_heading(paragraph):
                    self._flush_section(
                        sections=sections,
                        source_file=source_file,
                        current_title=current_title,
                        current_kind=current_kind,
                        current_parts=current_parts,
                        heading_stack=heading_stack,
                        section_counter=section_counter,
                    )
                    if current_parts:
                        section_counter += 1
                        current_parts = []
                    heading_stack = self._resolve_heading_path(heading_stack, text, paragraph["style"])
                    current_title = text
                    current_kind = "reference_content"
                    continue

                current_parts.append(self._normalise_paragraph_text(text, paragraph["style"]))
                continue

            if tag == "tbl":
                table_text = self._table_text(element)
                if table_text:
                    current_parts.append(table_text)

        self._flush_section(
            sections=sections,
            source_file=source_file,
            current_title=current_title,
            current_kind=current_kind,
            current_parts=current_parts,
            heading_stack=heading_stack,
            section_counter=section_counter,
        )

        return ParsedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            document_type=self.document_type,
            extracted_at=datetime.now(UTC),
            sections=sections,
            metadata={
                "subtype": "word_sectional_reference",
                "section_count": len(sections),
            },
        )

    def _flush_section(
        self,
        *,
        sections: list[ParsedSection],
        source_file: Path,
        current_title: str,
        current_kind: str,
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
                kind=current_kind,
                heading_path=tuple(heading_stack) if heading_stack else ((current_title,) if current_title else ()),
                structured_data={
                    "content_type": current_kind,
                    "source_format": "docx",
                    "section_title_normalized": normalized_title,
                },
            )
        )

    def _paragraph_data(self, paragraph: ET.Element) -> dict[str, str | bool | int]:
        style = self._paragraph_style(paragraph)
        text = "".join((node.text or "") for node in paragraph.findall(".//w:t", WORD_NS)).strip()

        total_runs = 0
        bold_runs = 0
        for run in paragraph.findall("./w:r", WORD_NS):
            total_runs += 1
            if run.find("./w:rPr/w:b", WORD_NS) is not None:
                bold_runs += 1

        return {
            "text": text,
            "style": style,
            "total_runs": total_runs,
            "bold_runs": bold_runs,
        }

    def _paragraph_style(self, paragraph: ET.Element) -> str:
        style = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
        if style is None:
            return ""
        return style.attrib.get(f"{{{WORD_NS['w']}}}val", "")

    def _is_heading(self, paragraph: dict[str, str | bool | int]) -> bool:
        text = str(paragraph["text"]).strip()
        style = str(paragraph["style"]).strip()
        total_runs = int(paragraph["total_runs"])
        bold_runs = int(paragraph["bold_runs"])

        if not text:
            return False
        if self._is_heading_style(style):
            return True
        if self._is_bold_standalone_heading(text=text, total_runs=total_runs, bold_runs=bold_runs):
            return True
        return self._looks_like_numbered_heading(text)

    def _is_heading_style(self, style: str) -> bool:
        normalised = style.lower()
        return bool(normalised) and any(
            token in normalised
            for token in ("heading", "subheading", "title")
        )

    def _is_bold_standalone_heading(self, *, text: str, total_runs: int, bold_runs: int) -> bool:
        if total_runs == 0 or bold_runs == 0 or bold_runs != total_runs:
            return False
        if len(text) > 120:
            return False
        if text.endswith((".", "?", ";", ":")):
            return False
        return len(text.split()) <= 12

    def _looks_like_numbered_heading(self, text: str) -> bool:
        return bool(re.match(r"^\d+(\.\d+)*\s+[A-Z][A-Za-z0-9 ,/&()-]+$", text))

    def _resolve_heading_path(self, heading_stack: list[str], title: str, style: str) -> list[str]:
        level = self._heading_level(style)
        if level is None:
            level = min(len(heading_stack) + 1, 3)

        base = heading_stack[: level - 1]
        base.append(title)
        return base

    def _heading_level(self, style: str) -> int | None:
        match = re.search(r"heading\s*([1-9])", style, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        if "subheading" in style.lower():
            return 2
        if "title" in style.lower():
            return 1
        return None

    def _normalise_paragraph_text(self, text: str, style: str) -> str:
        if style.lower().startswith("list") and not text.startswith(("-", "•")):
            return f"- {text}"
        return text

    def _table_text(self, table: ET.Element) -> str:
        rows: list[str] = []
        for row in table.findall("./w:tr", WORD_NS):
            cells: list[str] = []
            for cell in row.findall("./w:tc", WORD_NS):
                parts = []
                for paragraph in cell.findall(".//w:p", WORD_NS):
                    text = "".join((node.text or "") for node in paragraph.findall(".//w:t", WORD_NS)).strip()
                    if text:
                        parts.append(text)
                cell_text = " ".join(parts).strip()
                if cell_text:
                    cells.append(cell_text)
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows).strip()

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "section"
