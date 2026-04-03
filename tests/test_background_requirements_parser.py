from pathlib import Path
from zipfile import ZipFile

from rfp_rag_assistant.parsers import BackgroundRequirementsParser


def _write_minimal_docx(path: Path, document_xml: str) -> None:
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:styles>
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles_xml)


def test_background_requirements_parser_extracts_sections_from_heading_styles(tmp_path: Path) -> None:
    source = tmp_path / "background.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Service Overview</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>The service provides integrated wheelchair support.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="ListParagraph"/></w:pPr>
      <w:r><w:t>Responsive repair arrangements are required.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="NumberedSubheading"/></w:pPr>
      <w:r><w:t>IT considerations</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>BEST is the main clinical information system.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    _write_minimal_docx(source, document_xml)

    parsed = BackgroundRequirementsParser().parse_file(source)

    assert parsed.document_type == "background_requirements"
    assert parsed.metadata["subtype"] == "word_sectional_reference"
    assert parsed.metadata["section_count"] == 2
    assert parsed.sections[0].title == "Service Overview"
    assert parsed.sections[0].heading_path == ("Service Overview",)
    assert parsed.sections[0].structured_data["section_title_normalized"] == "Service Overview"
    assert "- Responsive repair arrangements are required." in parsed.sections[0].text
    assert parsed.sections[1].title == "IT considerations"
    assert parsed.sections[1].heading_path == ("Service Overview", "IT considerations")


def test_background_requirements_parser_detects_bold_standalone_heading(tmp_path: Path) -> None:
    source = tmp_path / "bold-heading.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:rPr><w:b/></w:rPr><w:t>Equality, diversity and health inequalities</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>The service should reduce variation and improve access.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>
"""
    _write_minimal_docx(source, document_xml)

    parsed = BackgroundRequirementsParser().parse_file(source)

    assert parsed.metadata["section_count"] == 1
    assert parsed.sections[0].title == "Equality, diversity and health inequalities"
    assert parsed.sections[0].heading_path == ("Equality, diversity and health inequalities",)
    assert parsed.sections[0].structured_data["section_title_normalized"] == "Equality, diversity and health inequalities"
    assert "improve access" in parsed.sections[0].text


def test_background_requirements_parser_extracts_real_background_document_sections() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/background_requirements/"
        "Background information - Wheelchair and Specialist Seating Service.docx"
    )

    parsed = BackgroundRequirementsParser().parse_file(source)

    assert parsed.document_type == "background_requirements"
    assert parsed.metadata["section_count"] >= 5
    titles = [section.title for section in parsed.sections]
    assert "Current services" in titles
    assert "IT considerations" in titles
