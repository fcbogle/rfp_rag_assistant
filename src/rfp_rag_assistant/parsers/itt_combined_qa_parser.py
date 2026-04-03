from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from rfp_rag_assistant.models import ParsedDocument, ParsedSection

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(slots=True)
class ITTCombinedQAParser:
    document_type: str = "combined_qa"
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def parse_file(self, source_file: Path) -> ParsedDocument:
        with ZipFile(source_file) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))

        question_id = ""
        question_title = ""
        question_text = ""
        response_started = False
        answer_text_from_table = ""
        answer_paragraphs: list[str] = []

        body = root.find(".//w:body", WORD_NS)
        if body is None:
            raise ValueError(f"Could not find Word document body in {source_file}")

        for element in body:
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "tbl" and not question_text:
                extracted = self._extract_question_from_table(element)
                question_id = extracted["question_id"]
                question_title = extracted["question_title"]
                question_text = extracted["question_text"]
                response_started = extracted["response_started"]
                answer_text_from_table = extracted["answer_text"]
                continue

            if tag != "p":
                continue

            text = self._paragraph_text(element)
            if not text:
                continue
            if text == "Response":
                response_started = True
                continue
            if response_started:
                answer_paragraphs.append(text)

        if not question_text:
            raise ValueError(f"Could not extract question text from {source_file}")

        answer_parts = []
        if answer_text_from_table:
            answer_parts.append(answer_text_from_table)
        if answer_paragraphs:
            answer_parts.append("\n\n".join(answer_paragraphs).strip())
        answer_text = "\n\n".join(part for part in answer_parts if part).strip()
        if not question_title:
            question_title = self._question_title_from_filename(source_file)
        title = " - ".join(part for part in (question_id, question_title) if part).strip() or source_file.stem
        self.logger.info(
            "Parsed ITT combined QA file=%s question_id=%s title=%s answer_chars=%s",
            source_file.name,
            question_id or "<missing>",
            question_title or "<missing>",
            len(answer_text),
        )

        return ParsedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            document_type=self.document_type,
            extracted_at=datetime.now(UTC),
            metadata={
                "subtype": "itt_structured_qa",
                "question_id": question_id,
                "question_title": question_title,
            },
            sections=[
                ParsedSection(
                    section_id=question_id or source_file.stem,
                    title=title,
                    text=answer_text,
                    kind="qa_pair",
                    structured_data={
                        "question_id": question_id,
                        "question_title": question_title,
                        "question_text": question_text,
                        "answer_text": answer_text,
                    },
                )
            ],
        )

    def _extract_question_from_table(self, table: ET.Element) -> dict[str, str | bool]:
        rows = [self._table_row_cells(row) for row in table.findall("./w:tr", WORD_NS)]
        flat_rows = [row for row in rows if any(cell.strip() for cell in row)]

        question_id = ""
        question_title = ""
        question_part = ""
        question_text_parts: list[str] = []
        answer_text_parts: list[str] = []
        response_started = False

        for row in flat_rows:
            cleaned = [cell.strip() for cell in row if cell.strip()]
            if not cleaned:
                continue
            lower = [cell.lower() for cell in cleaned]

            if cleaned == ["Response"]:
                response_started = True
                continue
            if cleaned == ["Question"]:
                continue
            if any(
                header in lower
                for header in (
                    "question number",
                    "detailed question",
                    "detailed question number",
                    "character count",
                    "word count",
                    "part",
                )
            ):
                continue
            if len(cleaned) >= 3 and cleaned[1].upper().startswith("ITT"):
                question_part = cleaned[0] if cleaned[0] and not cleaned[0].upper().startswith("ITT") else question_part
                question_id = cleaned[1]
                candidate_title = cleaned[2] if len(cleaned) >= 3 else ""
                question_title = candidate_title if not self._looks_like_count(candidate_title) else question_title
                continue
            if cleaned and cleaned[0].upper().startswith("ITT") and len(cleaned) >= 2:
                question_id = cleaned[0]
                question_title = cleaned[1] if not self._looks_like_count(cleaned[1]) else question_title
                continue
            if response_started:
                answer_text_parts.extend(cleaned)
                continue
            if "question" in lower or any("attachments:" in cell for cell in lower):
                question_text_parts.extend(cleaned)
                continue
            if not response_started and not question_text_parts:
                question_text_parts.extend(cleaned)

        question_text = "\n".join(part for part in question_text_parts if part and part != "Question").strip()
        if not question_title:
            question_title = question_part
        answer_text = "\n".join(part for part in answer_text_parts if part).strip()
        return {
            "question_id": question_id,
            "question_title": question_title,
            "question_text": question_text,
            "response_started": response_started,
            "answer_text": answer_text,
        }

    def _table_row_cells(self, row: ET.Element) -> list[str]:
        cells: list[str] = []
        for cell in row.findall("./w:tc", WORD_NS):
            parts = []
            for paragraph in cell.findall(".//w:p", WORD_NS):
                text = self._paragraph_text(paragraph)
                if text:
                    parts.append(text)
            cells.append(" | ".join(parts))
        return cells

    def _paragraph_text(self, paragraph: ET.Element) -> str:
        return "".join((text.text or "") for text in paragraph.findall(".//w:t", WORD_NS)).strip()

    def _question_title_from_filename(self, source_file: Path) -> str:
        stem = source_file.stem
        if "-" in stem:
            parts = [part.strip() for part in stem.split("-") if part.strip()]
            if len(parts) >= 2:
                candidate = parts[1]
                if candidate.lower() != "blatchford":
                    return candidate
        return stem

    def _looks_like_count(self, value: str) -> bool:
        compact = value.replace(" ", "")
        return bool(re.fullmatch(r"\d+/\d+", compact))
