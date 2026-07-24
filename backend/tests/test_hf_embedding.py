import pytest

from app.providers.impl.embedding_utils import normalize_dense, parse_batch_embeddings, pool_embedding


def test_pool_embedding_flat_vector():
    assert pool_embedding([0.3, 0.4]) == pytest.approx([0.6, 0.8])


def test_pool_embedding_token_matrix():
    pooled = pool_embedding([[1.0, 0.0], [0.0, 1.0]])
    assert pooled == pytest.approx([0.7071067811865475, 0.7071067811865475])


def test_parse_batch_embeddings():
    raw = [[0.6, 0.8], [0.8, 0.6]]
    parsed = parse_batch_embeddings(raw, expected=2)
    assert len(parsed) == 2
    assert parsed[0] == pytest.approx(normalize_dense([0.6, 0.8]))


@pytest.mark.asyncio
async def test_hf_embed_query_uses_api(monkeypatch):
    from app.providers.impl.hf_embedding import HuggingFaceEmbeddingProvider

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [0.6, 0.8]

    class FakeClient:
        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(
        "app.providers.impl.hf_embedding.settings.huggingface_api_key",
        "hf_test_token",
    )
    monkeypatch.setattr(
        "app.providers.impl.hf_embedding.get_async_http_client",
        lambda: FakeClient(),
    )

    provider = HuggingFaceEmbeddingProvider()
    dense, sparse = await provider.embed_query("hello world")

    assert dense == pytest.approx(normalize_dense([0.6, 0.8]))
    assert sparse
