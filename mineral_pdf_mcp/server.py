from mcp.server.fastmcp import FastMCP

from .service import extract_resources as extract_resources_service

mcp = FastMCP("mineral-pdf-mcp", json_response=True)


@mcp.tool()
async def extract_resources(pdf_url: str) -> dict:
    """Extract Indicated and Inferred mineral-resource rows with page evidence."""
    return await extract_resources_service(pdf_url)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
