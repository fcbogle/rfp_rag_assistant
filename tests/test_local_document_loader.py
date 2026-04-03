from pathlib import Path

from rfp_rag_assistant.loaders import LocalDocumentLoader


def test_local_document_loader_returns_path_payload() -> None:
    loader = LocalDocumentLoader()

    loaded = loader.load(Path("example.docx"))

    assert loaded.source_file == Path("example.docx")
    assert loaded.file_type == "docx"
    assert loaded.payload == Path("example.docx")
