from app.providers.impl.embedding_utils import query_text


def test_query_text_adds_prefix_when_configured(monkeypatch):
    monkeypatch.setattr(
        "app.providers.impl.embedding_utils.settings.embedding_query_prefix",
        "Represent this sentence for searching relevant passages: ",
    )
    assert query_text("what is attention?").startswith("Represent this sentence")


def test_query_text_unchanged_when_prefix_empty(monkeypatch):
    monkeypatch.setattr(
        "app.providers.impl.embedding_utils.settings.embedding_query_prefix",
        "",
    )
    assert query_text("what is attention?") == "what is attention?"
