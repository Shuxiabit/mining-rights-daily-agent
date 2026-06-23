from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def envelope(
    data: Any,
    *,
    source_url: str | None,
    data_status: str,
    error: str | None = None,
) -> dict[str, Any]:
    """Create the response contract shared by every MCP tool."""
    return {
        "data": data,
        "source_url": source_url,
        "retrieved_at": utc_now(),
        "data_status": data_status,
        "error": error,
    }
