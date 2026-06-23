from datetime import UTC, datetime

from mining_news_mcp.service import filter_articles, search_news


def test_news_filter_applies_query_and_date():
    articles = [
        {
            "title": "Pilbara lithium update",
            "summary": "Mine expansion",
            "url": "https://example.com/1",
            "published_at": "2026-06-22T00:00:00+00:00",
        },
        {
            "title": "Old Pilbara item",
            "summary": "Lithium",
            "url": "https://example.com/2",
            "published_at": "2025-01-01T00:00:00+00:00",
        },
        {
            "title": "Copper update",
            "summary": "Chile",
            "url": "https://example.com/3",
            "published_at": "2026-06-22T00:00:00+00:00",
        },
    ]
    result = filter_articles(
        articles,
        "Pilbara lithium",
        7,
        now=datetime(2026, 6, 23, tzinfo=UTC),
    )
    assert [item["url"] for item in result] == ["https://example.com/1"]


async def test_live_news_failure_does_not_return_demo(monkeypatch):
    async def fail(*args, **kwargs):
        raise ValueError("blocked")

    monkeypatch.delenv("MINING_AGENT_OFFLINE", raising=False)
    monkeypatch.setattr("mining_news_mcp.service.fetch_public", fail)
    result = await search_news("Pilbara lithium", 7)
    assert result["data_status"] == "unavailable"
    assert result["data"] == []
