import logging
import time
from functools import lru_cache
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.providers.base import VectorStore
from app.providers.types import ChunkPayload, RetrievedChunk

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None


def _get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url)
    return _client


class QdrantVectorStore(VectorStore):
    """Async Qdrant store with hybrid dense + sparse search."""

    async def _collection_exists(self) -> bool:
        client = _get_client()
        collections = await client.get_collections()
        return settings.qdrant_collection in {c.name for c in collections.collections}

    async def ensure_collection(self) -> None:
        client = _get_client()
        collections = await client.get_collections()
        names = {c.name for c in collections.collections}
        if settings.qdrant_collection in names:
            return

        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                "dense": qmodels.VectorParams(
                    size=settings.embedding_dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": qmodels.SparseVectorParams(
                    index=qmodels.SparseIndexParams(on_disk=False),
                ),
            },
        )
        logger.info("Created Qdrant collection: %s", settings.qdrant_collection)

    async def upsert(self, chunks: list[ChunkPayload]) -> None:
        if not chunks:
            return
        await self.ensure_collection()
        client = _get_client()
        t0 = time.perf_counter()

        points = []
        for chunk in chunks:
            vector: dict = {"dense": chunk.dense_vector}
            if chunk.sparse_vector:
                vector["sparse"] = qmodels.SparseVector(
                    indices=list(chunk.sparse_vector.keys()),
                    values=list(chunk.sparse_vector.values()),
                )
            points.append(
                qmodels.PointStruct(
                    id=str(chunk.chunk_id),
                    vector=vector,
                    payload={
                        "project_id": str(chunk.project_id),
                        "document_id": str(chunk.document_id),
                        "filename": chunk.filename,
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "section_heading": chunk.section_heading,
                        "content": chunk.content,
                        "source": "document",
                    },
                )
            )

        await client.upsert(collection_name=settings.qdrant_collection, points=points)
        logger.info("Qdrant upsert (%d points): %.1fms", len(points), (time.perf_counter() - t0) * 1000)

    def _build_filter(
        self, project_id: UUID, document_ids: list[UUID] | None
    ) -> qmodels.Filter:
        must = [
            qmodels.FieldCondition(
                key="project_id",
                match=qmodels.MatchValue(value=str(project_id)),
            )
        ]
        if document_ids:
            must.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=[str(d) for d in document_ids]),
                )
            )
        return qmodels.Filter(must=must)

    async def search(
        self,
        project_id: UUID,
        dense_vector: list[float],
        sparse_vector: dict[int, float] | None,
        limit: int,
        document_ids: list[UUID] | None = None,
    ) -> list[RetrievedChunk]:
        await self.ensure_collection()
        client = _get_client()
        t0 = time.perf_counter()
        query_filter = self._build_filter(project_id, document_ids)

        if sparse_vector:
            results = await client.query_points(
                collection_name=settings.qdrant_collection,
                prefetch=[
                    qmodels.Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=limit,
                        filter=query_filter,
                    ),
                    qmodels.Prefetch(
                        query=qmodels.SparseVector(
                            indices=list(sparse_vector.keys()),
                            values=list(sparse_vector.values()),
                        ),
                        using="sparse",
                        limit=limit,
                        filter=query_filter,
                    ),
                ],
                query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                limit=limit,
                with_payload=True,
            )
            points = results.points
        else:
            results = await client.query_points(
                collection_name=settings.qdrant_collection,
                query=dense_vector,
                using="dense",
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            points = results.points

        chunks: list[RetrievedChunk] = []
        for point in points:
            payload = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=UUID(str(point.id)),
                    document_id=UUID(payload["document_id"]),
                    project_id=UUID(payload["project_id"]),
                    filename=payload.get("filename", ""),
                    content=payload.get("content", ""),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    page_number=payload.get("page_number"),
                    section_heading=payload.get("section_heading"),
                    score=float(point.score or 0.0),
                    source=payload.get("source", "document"),
                )
            )

        logger.info("Qdrant search: %.1fms (%d results)", (time.perf_counter() - t0) * 1000, len(chunks))
        return chunks

    async def delete_document(self, document_id: UUID) -> None:
        if not await self._collection_exists():
            return
        client = _get_client()
        await client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    async def delete_project(self, project_id: UUID) -> None:
        if not await self._collection_exists():
            return
        client = _get_client()
        await client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="project_id",
                            match=qmodels.MatchValue(value=str(project_id)),
                        )
                    ]
                )
            ),
        )


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return QdrantVectorStore()
