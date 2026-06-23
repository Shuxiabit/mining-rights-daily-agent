from mcp.server.fastmcp import FastMCP

from .service import fetch_article as fetch_article_service
from .service import search_news

mcp = FastMCP("mining-news-mcp", json_response=True)


@mcp.tool()
async def search(query: str, days: int = 7) -> dict:
    """Search recent public mining news. Results identify live versus demo data."""
    return await search_news(query, days)


@mcp.tool()
async def fetch_article(url: str) -> dict:
    """Fetch readable article text from a public URL."""
    return await fetch_article_service(url)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
