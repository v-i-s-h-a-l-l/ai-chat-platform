"""Prometheus metrics for production observability."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Info

SERVICE_INFO = Info("chatbot_service", "Chatbot service metadata")

HTTP_REQUESTS = Counter(
    "chatbot_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "chatbot_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

CHAT_CONTEXT_DURATION = Histogram(
    "chatbot_chat_context_duration_seconds",
    "Time to prepare RAG/routing context before LLM",
    ["routing_enabled"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

CHAT_TTFT = Histogram(
    "chatbot_chat_ttft_seconds",
    "Time to first streamed token (approx: context + first token)",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
)

CHAT_REQUESTS = Counter(
    "chatbot_chat_requests_total",
    "Chat requests by outcome",
    ["outcome"],
)

RAG_DURATION = Histogram(
    "chatbot_rag_duration_seconds",
    "RAG retrieval pipeline duration",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

RAG_CHUNKS = Histogram(
    "chatbot_rag_chunks_returned",
    "Number of chunks returned by RAG",
    buckets=(0, 1, 2, 3, 5, 8, 13, 20),
)

INGESTION_ENQUEUED = Counter(
    "chatbot_ingestion_enqueued_total",
    "Documents successfully enqueued for ingestion",
)

INGESTION_ENQUEUE_FAILURES = Counter(
    "chatbot_ingestion_enqueue_failures_total",
    "Failed attempts to enqueue document ingestion",
)

INGESTION_INLINE_FALLBACK = Counter(
    "chatbot_ingestion_inline_fallback_total",
    "Ingestion jobs that ran inside the API process (dev fallback)",
)


def init_service_info(*, environment: str, version: str = "1.0.0") -> None:
    SERVICE_INFO.info({"environment": environment, "version": version})
