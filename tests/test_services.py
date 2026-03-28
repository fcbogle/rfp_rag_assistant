from rfp_rag_assistant.config import AppSettings, ChromaSettings, RetrievalSettings
from rfp_rag_assistant.services import AppContainer


def test_app_container_builds_service_graph() -> None:
    settings = AppSettings(
        chroma=ChromaSettings(collection="rfp_answers"),
        retrieval=RetrievalSettings(default_top_k=7),
    )

    container = AppContainer.build(settings)

    assert container.health_service.check()["config_loaded"] is True
    assert container.query_service.settings.retrieval.default_top_k == 7
