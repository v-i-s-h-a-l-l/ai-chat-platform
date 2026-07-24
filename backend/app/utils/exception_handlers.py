"""Centralized FastAPI exception handlers for domain errors."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.guardrails.exceptions import GuardrailViolationError
from app.services.ingestion_errors import IngestionQueueUnavailableError
from app.services.upload_validation.exceptions import UploadConfirmationRequiredError


async def guardrail_violation_handler(
    _request: Request,
    exc: GuardrailViolationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def upload_confirmation_required_handler(
    _request: Request,
    exc: UploadConfirmationRequiredError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": {
                "message": exc.message,
                "code": exc.code,
                "document_type": exc.document_type,
                "confidence": exc.confidence,
            }
        },
    )


async def ingestion_queue_unavailable_handler(
    _request: Request,
    exc: IngestionQueueUnavailableError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(GuardrailViolationError, guardrail_violation_handler)
    app.add_exception_handler(
        UploadConfirmationRequiredError,
        upload_confirmation_required_handler,
    )
    app.add_exception_handler(
        IngestionQueueUnavailableError,
        ingestion_queue_unavailable_handler,
    )
