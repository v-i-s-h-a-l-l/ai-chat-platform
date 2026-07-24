"""OpenTelemetry tracing helpers (optional OTLP export)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from app.config import settings

logger = logging.getLogger(__name__)

_tracer = None
_initialized = False


def setup_tracing() -> None:
    """Initialize OpenTelemetry when enabled. Safe no-op when disabled."""
    global _tracer, _initialized
    if _initialized:
        return
    _initialized = True

    if not settings.otel_enabled:
        logger.info("OpenTelemetry tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create(
            {
                "service.name": settings.otel_service_name,
                "deployment.environment": settings.environment,
            }
        )
        provider = TracerProvider(resource=resource)

        if settings.otel_exporter_otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OpenTelemetry OTLP exporter → %s", settings.otel_exporter_otlp_endpoint)
        elif settings.otel_console_export:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("OpenTelemetry console exporter enabled")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("chatbot")
        logger.info("OpenTelemetry tracing enabled")
    except Exception:
        logger.exception("Failed to initialize OpenTelemetry — continuing without tracing")
        _tracer = None


def get_tracer():
    return _tracer


@contextmanager
def span(name: str, **attributes: object) -> Iterator[None]:
    """Create a span when tracing is active; otherwise no-op."""
    tracer = _tracer
    if tracer is None:
        yield
        return

    from opentelemetry import trace

    with tracer.start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value)
        try:
            yield
        except Exception as exc:
            current.record_exception(exc)
            current.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise


async def async_span(name: str, **attributes: object):
    """Async context manager wrapper around span()."""
    return _AsyncSpan(name, attributes)


class _AsyncSpan:
    def __init__(self, name: str, attributes: dict[str, object]) -> None:
        self._name = name
        self._attributes = attributes
        self._cm = span(name, **attributes)

    async def __aenter__(self):
        self._cm.__enter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return self._cm.__exit__(exc_type, exc, tb)
