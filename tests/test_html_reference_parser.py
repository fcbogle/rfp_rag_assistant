from pathlib import Path

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.parsers import HTMLReferenceParser


def test_html_reference_parser_extracts_sections_and_skips_boilerplate() -> None:
    html = """
    <html>
      <head><title>Core20PLUS5 Guidance</title><style>.x { color: red; }</style></head>
      <body>
        <nav>Navigation links</nav>
        <main>
          <h1>Core20PLUS5</h1>
          <p>The programme aims to reduce healthcare inequalities.</p>
          <h2>Approach</h2>
          <p>Providers should focus on the most deprived populations.</p>
          <ul><li>Use data</li><li>Target interventions</li></ul>
        </main>
        <footer>Footer text</footer>
      </body>
    </html>
    """
    parser = HTMLReferenceParser()
    loaded = LoadedDocument(
        source_file=Path("external_reference/www.england.nhs.uk/core20plus5.html"),
        file_type="html",
        payload=html,
        metadata={
            "source_url": "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
            "source_domain": "www.england.nhs.uk",
            "reference_origin": "customer_cited",
        },
    )

    parsed = parser.parse(loaded)

    assert parsed.document_type == "external_reference"
    assert parsed.metadata["page_title"] == "Core20PLUS5 Guidance"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].title == "Core20PLUS5"
    assert "reduce healthcare inequalities" in parsed.sections[0].text
    assert parsed.sections[1].title == "Approach"
    assert "Target interventions" in parsed.sections[1].text
    assert parsed.sections[0].structured_data["section_title_normalized"] == "Core20PLUS5"
    assert parsed.sections[0].structured_data["reference_origin"] == "customer_cited"


def test_html_reference_parser_drops_cookie_and_menu_sections() -> None:
    html = """
    <html>
      <head><title>One Child One Chair | Posture and Mobility Group</title></head>
      <body>
        <h1>Cookies on this site</h1>
        <p>Change my preferences</p>
        <p>I'm OK with analytics cookies</p>
        <h1>One Child One Chair | Posture and Mobility Group</h1>
        <ul>
          <li>Home</li>
          <li>Donate</li>
          <li>Membership Benefits</li>
          <li>Executive Committee</li>
          <li>Poster Presentations</li>
          <li>Webcasts</li>
          <li>External Training Events</li>
          <li>Associated papers</li>
          <li>Submit a News Item</li>
          <li>Published 2025</li>
          <li>Published 2024</li>
          <li>Accounts</li>
        </ul>
        <h2>Clinical context</h2>
        <p>Children with complex postural needs benefit from early intervention and appropriate seating provision.</p>
      </body>
    </html>
    """
    parser = HTMLReferenceParser()
    loaded = LoadedDocument(
        source_file=Path("external_reference/www.pmguk.co.uk/one-child-one-chair.html"),
        file_type="html",
        payload=html,
        metadata={
            "source_url": "https://www.pmguk.co.uk/journals/one-child-one-chair",
            "source_domain": "www.pmguk.co.uk",
            "reference_origin": "customer_cited",
        },
    )

    parsed = parser.parse(loaded)

    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "Clinical context"
    assert "early intervention" in parsed.sections[0].text


def test_html_reference_parser_drops_generic_listing_sections() -> None:
    html = """
    <html>
      <head><title>One Child One Chair | Posture and Mobility Group</title></head>
      <body>
        <h2>Journal</h2>
        <p>Guidance</p>
        <p>PMG Journal: 1997 - 2014</p>
        <h2>FEATURED JOURNAL ARTICLE</h2>
        <p>Reflective article: Improving Service Efficiency and Quality</p>
        <p>Robert Cheval - Associate Clinical Technologist</p>
      </body>
    </html>
    """
    parser = HTMLReferenceParser()
    loaded = LoadedDocument(
        source_file=Path("external_reference/www.pmguk.co.uk/one-child-one-chair.html"),
        file_type="html",
        payload=html,
        metadata={
            "source_url": "https://www.pmguk.co.uk/journals/one-child-one-chair",
            "source_domain": "www.pmguk.co.uk",
            "reference_origin": "customer_cited",
        },
    )

    parsed = parser.parse(loaded)

    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "FEATURED JOURNAL ARTICLE"
    assert "Improving Service Efficiency and Quality" in parsed.sections[0].text


def test_html_reference_parser_drops_promotional_sections() -> None:
    html = """
    <html>
      <head><title>One Child One Chair | Posture and Mobility Group</title></head>
      <body>
        <h2>PMG2026 Training | Conference | Exhibition</h2>
        <p>Our annual event provides an educational programme, industry exhibition and networking opportunities.</p>
        <h2>One Child One Chair</h2>
        <p>Alex Freeman</p>
        <p>Occupational Therapist</p>
        <p>15 April 2019</p>
        <p>I have been a qualified occupational therapist since 2002 working within the NHS.</p>
      </body>
    </html>
    """
    parser = HTMLReferenceParser()
    loaded = LoadedDocument(
        source_file=Path("external_reference/www.pmguk.co.uk/one-child-one-chair.html"),
        file_type="html",
        payload=html,
        metadata={
            "source_url": "https://www.pmguk.co.uk/journals/one-child-one-chair",
            "source_domain": "www.pmguk.co.uk",
            "reference_origin": "customer_cited",
        },
    )

    parsed = parser.parse(loaded)

    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "One Child One Chair"
    assert "qualified occupational therapist" in parsed.sections[0].text
