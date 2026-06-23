from mcp.server.fastmcp import FastMCP

from .service import get_price_data, get_trend_data

mcp = FastMCP("lme-price-mcp", json_response=True)


@mcp.tool()
async def get_price(commodity: str, date: str | None = None) -> dict:
    """Get the closest available public market observation for a commodity or disclosed proxy."""
    return await get_price_data(commodity, date)


@mcp.tool()
async def get_trend(commodity: str, days: int = 30) -> dict:
    """Get a public commodity/proxy price series and calculated trend."""
    return await get_trend_data(commodity, days)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
