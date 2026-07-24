"""Upload validation exceptions."""

from __future__ import annotations


class UploadConfirmationRequiredError(Exception):
    """Raised when upload needs explicit user confirmation before indexing."""

    def __init__(
        self,
        message: str,
        *,
        document_type: str | None = None,
        confidence: float | None = None,
    ) -> None:
        self.message = message
        self.document_type = document_type
        self.confidence = confidence
        self.code = "upload_confirmation_required"
        super().__init__(message)
