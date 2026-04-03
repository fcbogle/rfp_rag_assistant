from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from rfp_rag_assistant.models import ParsedDocument, ParsedSection

WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(slots=True)
class NarrativeCombinedQAParser:
    document_type: str = "combined_qa"

    def parse_file(self, source_file: Path) -> ParsedDocument:
        paragraphs = self._extract_paragraphs(source_file)
        if not paragraphs:
            raise ValueError(f"Could not extract narrative content from {source_file}")

        question_id = self._question_id_from_filename(source_file)
        question_title = self._question_title_from_filename(source_file)
        question_text, answer_text = self._split_question_and_answer(paragraphs)
        if not answer_text:
            raise ValueError(f"Could not extract answer text from {source_file}")

        title = " - ".join(part for part in (question_id, question_title) if part).strip() or source_file.stem
        answer_paragraph_count = len([part for part in answer_text.split("\n\n") if part.strip()])

        return ParsedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            document_type=self.document_type,
            extracted_at=datetime.now(UTC),
            metadata={
                "subtype": "narrative_combined_qa",
                "question_id": question_id,
                "question_title": question_title,
                "answer_paragraph_count": answer_paragraph_count,
            },
            sections=[
                ParsedSection(
                    section_id=question_id or self._slugify(source_file.stem),
                    title=title,
                    text=answer_text,
                    kind="qa_pair",
                    structured_data={
                        "question_id": question_id,
                        "question_title": question_title,
                        "question_text": question_text,
                        "answer_text": answer_text,
                        "answer_paragraph_count": answer_paragraph_count,
                    },
                )
            ],
        )

    def _extract_paragraphs(self, source_file: Path) -> list[str]:
        with ZipFile(source_file) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))

        paragraphs: list[str] = []
        body = root.find(".//w:body", WORD_NS)
        if body is None:
            return paragraphs

        for element in body:
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = self._paragraph_text(element)
                if text:
                    paragraphs.append(text)
            elif tag == "tbl":
                for row in element.findall("./w:tr", WORD_NS):
                    row_text = " | ".join(
                        cell_text
                        for cell_text in (self._table_cell_text(cell) for cell in row.findall("./w:tc", WORD_NS))
                        if cell_text
                    ).strip()
                    if row_text:
                        paragraphs.append(row_text)
        return paragraphs

    def _split_question_and_answer(self, paragraphs: list[str]) -> tuple[str, str]:
        title = paragraphs[0]
        body = paragraphs[1:] if len(paragraphs) > 1 else []

        question_parts: list[str] = []
        answer_parts: list[str] = []
        answer_started = False

        for paragraph in body:
            compact = paragraph.strip()
            if not compact:
                continue
            if self._is_separator(compact):
                answer_started = True
                continue
            if compact.lower() == "response":
                answer_started = True
                continue
            if not answer_started and self._looks_like_word_count(compact):
                answer_started = True
                continue
            if answer_started:
                answer_parts.append(compact)
            else:
                question_parts.append(compact)

        question_text = "\n".join(part for part in question_parts if part).strip()
        answer_text = "\n\n".join(part for part in answer_parts if part).strip()

        if not answer_text and question_parts:
            split_index = max(1, len(question_parts) // 2)
            question_text = "\n".join(question_parts[:split_index]).strip()
            answer_text = "\n\n".join(question_parts[split_index:]).strip()

        if not question_text:
            question_text = title

        return question_text, answer_text

    def _paragraph_text(self, paragraph: ET.Element) -> str:
        return "".join((text.text or "") for text in paragraph.findall(".//w:t", WORD_NS)).strip()

    def _table_cell_text(self, cell: ET.Element) -> str:
        return " ".join(
            text
            for text in (self._paragraph_text(paragraph) for paragraph in cell.findall(".//w:p", WORD_NS))
            if text
        ).strip()

    def _question_id_from_filename(self, source_file: Path) -> str:
        match = re.match(r"^(\d+(?:\.\d+)*)", source_file.stem)
        return match.group(1) if match else ""

    def _question_title_from_filename(self, source_file: Path) -> str:
        match = re.match(r"^\d+(?:\.\d+)*\s+(.*)$", source_file.stem)
        return match.group(1).strip() if match else source_file.stem

    def _looks_like_word_count(self, paragraph: str) -> bool:
        stripped = paragraph.strip()
        return bool(
            re.fullmatch(r"\d+/\d+\s*Words?.*", stripped, flags=re.IGNORECASE)
            or re.fullmatch(r"\d+/\d+", stripped)
        )

    def _is_separator(self, paragraph: str) -> bool:
        return bool(re.fullmatch(r"[_\-=]{5,}", paragraph.strip()))

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "combined-qa"
