from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
from bs4 import BeautifulSoup

from common.http import fetch_public, offline_mode
from common.models import envelope

DEMO_ARTICLES = [
    {
        "title": "Pilbara lithium producer outlines disciplined expansion plan",
        "url": "https://example.com/demo/pilbara-expansion",
        "published_at": "2026-06-21T00:00:00+00:00",
        "summary": (
            "Demonstration record: management prioritises staged expansion "
            "and balance-sheet resilience."
        ),
    },
    {
        "title": "Western Australia reviews critical-minerals approvals pathway",
        "url": "https://example.com/demo/wa-policy",
        "published_at": "2026-06-19T00:00:00+00:00",
        "summary": (
            "Demonstration record: proposed coordination may shorten approvals "
            "while preserving environmental review."
        ),
    },
    {
        "title": "Lithium market remains volatile as supply growth meets cautious demand",
        "url": "https://example.com/demo/lithium-market",
        "published_at": "2026-06-17T00:00:00+00:00",
        "summary": (
            "Demonstration record: prices remain sensitive to inventory, "
            "project delays and EV demand."
        ),
    },
]


def _matches(article: dict, query: str) -> bool:
    terms = [term.lower() for term in query.split() if len(term) > 2]
    haystack = f"{article['title']} {article.get('summary', '')}".lower()
    return not terms or any(term in haystack for term in terms)


def filter_articles(
    articles: list[dict], query: str, days: int, now: datetime | None = None
) -> list[dict]:
    cutoff = (now or datetime.now(UTC)) - timedelta(days=max(1, days))
    selected = []
    for article in articles:
        try:
            published = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if published >= cutoff and _matches(article, query):
            selected.append(article)
    return sorted(selected, key=lambda item: item["published_at"], reverse=True)


async def search_news(query: str, days: int = 7) -> dict:
    if offline_mode():
        return envelope(
            filter_articles(DEMO_ARTICLES, query, 3650),
            source_url=None,
            data_status="demo",
            error="Outbound requests disabled by MINING_AGENT_OFFLINE.",
        )

    rss_url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query + ' mining when:' + str(max(1, days)) + 'd')}&hl=en-AU&gl=AU&ceid=AU:en"
    )
    try:
        content, final_url, _ = await fetch_public(
            rss_url,
            allowed_content_types=("xml", "rss", "atom"),
            max_bytes=2_000_000,
        )
        feed = feedparser.parse(content)
        articles = []
        for entry in feed.entries[:20]:
            published = parsedate_to_datetime(entry.published).astimezone(UTC)
            articles.append(
                {
                    "title": entry.title,
                    "url": entry.link,
                    "published_at": published.isoformat(),
                    "summary": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(
                        " ", strip=True
                    ),
                }
            )
        return envelope(
            filter_articles(articles, query, days),
            source_url=final_url,
            data_status="live",
        )
    except Exception as exc:
        return envelope(
            [],
            source_url=rss_url,
            data_status="unavailable",
            error=f"Live news unavailable: {exc}",
        )


async def fetch_article(url: str) -> dict:
    demo = next((item for item in DEMO_ARTICLES if item["url"] == url), None)
    if offline_mode() or demo:
        item = demo or {
            "title": "Unavailable article",
            "summary": "No offline copy is available.",
            "url": url,
        }
        return envelope(
            {"title": item["title"], "text": item.get("summary", ""), "url": url},
            source_url=url,
            data_status="demo",
            error=None if demo else "Outbound requests disabled and no cached copy exists.",
        )
    try:
        content, final_url, _ = await fetch_public(
            url,
            allowed_content_types=("text/html", "application/xhtml+xml"),
            max_bytes=3_000_000,
        )
        soup = BeautifulSoup(content, "html.parser")
        for node in soup(["script", "style", "nav", "footer", "aside"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = "\n".join(part for part in paragraphs if len(part) > 40)[:12000]
        return envelope(
            {"title": title, "text": text, "url": final_url},
            source_url=final_url,
            data_status="live",
        )
    except Exception as exc:
        return envelope(
            {"title": "Article fetch failed", "text": "", "url": url},
            source_url=url,
            data_status="unavailable",
            error=str(exc),
        )
