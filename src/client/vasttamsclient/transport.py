import httpx


class HttpxTransport:
    """
    Thin wrapper around `httpx.AsyncClient` to provide pooled HTTP transport.

    The transport centralizes client configuration so higher-level code can
    inject request settings (timeouts, connection limits, TLS verification)
    without managing client lifecycle in each call site.
    """

    def __init__(
        self,
        timeout: int = 60,
        verify_ssl: bool = True,
        limit: int = 100,
        limit_per_host: int = 30,
        keepalive_timeout: int = 60,
    ):
        """
        Initialize transport with pooled async client settings.

        Args:
            timeout: Total request timeout (seconds) applied by httpx.
            verify_ssl: Whether to verify TLS certificates.
            limit: Maximum total concurrent connections.
            limit_per_host: Maximum concurrent connections per host.
            keepalive_timeout: Keep-alive expiry (seconds) for idle connections.
        """
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
            limits=httpx.Limits(
                max_connections=limit,
                max_keepalive_connections=limit_per_host,
                keepalive_expiry=keepalive_timeout,
            ),
        )

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Send an HTTP request using the shared AsyncClient.

        Args:
            method: HTTP method (e.g., "GET", "POST").
            url: Absolute URL to request.
            **kwargs: Additional httpx request options (headers, json, params, files, timeout, etc.).

        Returns:
            httpx.Response: The response returned by the server.
        """
        return await self._client.request(method, url, **kwargs)

    async def close(self):
        """
        Close the underlying AsyncClient.

        Should be called once the transport is no longer needed to release
        connection pool resources.
        """
        await self._client.aclose()

