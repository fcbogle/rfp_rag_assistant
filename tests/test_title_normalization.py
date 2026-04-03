from rfp_rag_assistant.parsers.title_normalization import normalize_section_title


def test_normalize_section_title_handles_all_caps_titles() -> None:
    assert normalize_section_title("TENDER TIMETABLE") == "Tender Timetable"
    assert normalize_section_title("INTRODUCTION AND BACKGROUND") == "Introduction and Background"


def test_normalize_section_title_preserves_existing_mixed_case_titles() -> None:
    assert normalize_section_title("Current services") == "Current services"
    assert normalize_section_title("IT considerations") == "IT considerations"
    assert normalize_section_title("Core20PLUS5") == "Core20PLUS5"
