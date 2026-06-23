from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse

import httpx


def offline_mode() -> bool:
    return os.getenv("MINING_AGENT_OFFLINE", "0").lower() in {"1", "true", "yes"}


def timeout_seconds() -> float:
    return float(os.getenv("HTTP_TIMEOUT_SECONDS", "12"))


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout_seconds(),
        follow_redirects=False,
        headers={"User-Agent": "mining-rights-daily-agent/0.1 (+educational demo)"},
    )


async def validate_public_url(url: str) -> None:
    """Reject non-HTTP and non-public destinations before an outbound request."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public http/https URLs are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")

    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ValueError("URL host could not be resolved.") from exc

    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Private, loopback, link-local, or reserved hosts are not allowed.")


async def fetch_public(
    url: str,
    *,
    allowed_content_types: tuple[str, ...],
    max_bytes: int,
    max_redirects: int = 3,
) -> tuple[bytes, str, str]:
    """Fetch a bounded public resource while validating every redirect target."""
    current_url = url
    async with client() as http:
        for _ in range(max_redirects + 1):
            await validate_public_url(current_url)
            async with http.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect response did not include a location.")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if not any(kind in content_type for kind in allowed_content_types):
                    raise ValueError(f"Unexpected content type: {content_type or 'missing'}")

                declared_size = int(response.headers.get("content-length", "0") or 0)
                if declared_size > max_bytes:
                    raise ValueError(f"Response exceeds {max_bytes} bytes.")

                chunks: list[bytes] = []
                received = 0
                async for chunk in response.aiter_bytes():
                    received += len(chunk)
                    if received > max_bytes:
                        raise ValueError(f"Response exceeds {max_bytes} bytes.")
                    chunks.append(chunk)
                return b"".join(chunks), str(response.url), content_type

    raise ValueError("Too many redirects.")
