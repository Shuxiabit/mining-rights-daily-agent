import httpx
import pytest

from common.http import fetch_public, validate_public_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/admin",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data",
    ],
)
async def test_rejects_non_public_urls(url):
    with pytest.raises(ValueError):
        await validate_public_url(url)


async def test_fetch_public_accepts_bounded_html(monkeypatch):
    async def allow(url):
        return None

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": "5"},
            content=b"hello",
            request=request,
        )

    monkeypatch.setattr("common.http.validate_public_url", allow)
    monkeypatch.setattr(
        "common.http.client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    content, final_url, content_type = await fetch_public(
        "https://example.com/article",
        allowed_content_types=("text/html",),
        max_bytes=10,
    )
    assert content == b"hello"
    assert final_url == "https://example.com/article"
    assert content_type == "text/html"


async def test_fetch_public_validates_redirect_and_content_type(monkeypatch):
    visited = []

    async def allow(url):
        visited.append(url)

    def handler(request):
        if str(request.url).endswith("/start"):
            return httpx.Response(302, headers={"location": "/final"}, request=request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{}",
            request=request,
        )

    monkeypatch.setattr("common.http.validate_public_url", allow)
    monkeypatch.setattr(
        "common.http.client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ValueError, match="Unexpected content type"):
        await fetch_public(
            "https://example.com/start",
            allowed_content_types=("text/html",),
            max_bytes=10,
        )
    assert visited == ["https://example.com/start", "https://example.com/final"]


async def test_fetch_public_rejects_oversized_response(monkeypatch):
    async def allow(url):
        return None

    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf", "content-length": "100"},
            content=b"x" * 100,
            request=request,
        )

    monkeypatch.setattr("common.http.validate_public_url", allow)
    monkeypatch.setattr(
        "common.http.client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ValueError, match="exceeds"):
        await fetch_public(
            "https://example.com/report.pdf",
            allowed_content_types=("application/pdf",),
            max_bytes=10,
        )
