import httpx

_async_client: httpx.AsyncClient | None = None


def get_async_http_client() -> httpx.AsyncClient:
    """Shared async client — reused across requests to avoid TCP/TLS handshakes per call."""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _async_client


async def close_async_http_client() -> None:
    global _async_client
    if _async_client is not None and not _async_client.is_closed:
        await _async_client.aclose()
    _async_client = None
