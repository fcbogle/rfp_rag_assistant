from pathlib import Path

from rfp_rag_assistant.loaders import ExternalReferenceLoader


def test_external_reference_loader_builds_virtual_source_and_metadata() -> None:
    loader = ExternalReferenceLoader(fetch_html=lambda _: "<html><title>Example</title></html>")

    loaded = loader.load_url(
        "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
        reference_origin="customer_cited",
        referenced_from_file=Path("background_requirements/source.docx"),
        referenced_from_classification="background_requirements",
    )

    assert loaded.file_type == "html"
    assert loaded.source_file.as_posix().startswith("external_reference/www.england.nhs.uk/")
    assert loaded.metadata["source_domain"] == "www.england.nhs.uk"
    assert loaded.metadata["reference_origin"] == "customer_cited"
    assert loaded.metadata["referenced_from_classification"] == "background_requirements"
