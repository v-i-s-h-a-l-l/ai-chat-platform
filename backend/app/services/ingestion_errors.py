"""Queue errors for document ingestion."""


class IngestionQueueUnavailableError(RuntimeError):
    """Raised when Redis/Arq cannot accept an ingestion job and inline fallback is disabled."""

    def __init__(self, document_id: str, cause: BaseException | None = None) -> None:
        self.document_id = document_id
        self.cause = cause
        super().__init__(
            "Document ingestion queue is unavailable. "
            "Ensure Redis and the ingestion worker are running, then retry."
        )
