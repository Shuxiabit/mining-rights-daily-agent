from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from common.http import client, offline_mode
from common.models import envelope

SYMBOLS = {
    "copper": ("HG=F", "USD/lb", "COMEX copper futures"),
    "lithium": ("LIT", "USD/share", "Global X Lithium & Battery Tech ETF proxy"),
    "nickel": ("NICK.L", "GBP/share", "WisdomTree Nickel ETC proxy"),
    "zinc": ("ZINC.L", "GBP/share", "WisdomTree Zinc ETC proxy"),
}

DEMO_SERIES = {
    "lithium": [38.2, 37.9, 38.5, 39.1, 38.7, 39.6, 40.0],
    "copper": [4.52, 4.55, 4.49, 4.61, 4.66, 4.63, 4.71],
    "nickel": [15.1, 15.0, 15.3, 15.2, 15.5, 15.4, 15.7],
    "zinc": [2.64, 2.62, 2.68, 2.70, 2.67, 2.72, 2.75],
}


def calculate_trend(values: list[float]) -> dict:
    if not values:
        return {"start": None, "end": None, "change_pct": None, "direction": "unknown"}
    start, end = values[0], values[-1]
    change = ((end - start) / start * 100) if start else 0.0
    direction = "up" if change > 0.25 else "down" if change < -0.25 else "flat"
    return {"start": start, "end": end, "change_pct": round(change, 2), "direction": direction}


def _demo_points(commodity: str, days: int) -> list[dict]:
    values = DEMO_SERIES.get(commodity, DEMO_SERIES["lithium"])
    end = date.today()
    selected = (values * ((days // len(values)) + 1))[-max(1, days) :]
    return [
        {"date": (end - timedelta(days=len(selected) - index - 1)).isoformat(), "close": value}
        for index, value in enumerate(selected)
    ]


async def _live_points(commodity: str, days: int) -> tuple[list[dict], str, str]:
    symbol, unit, label = SYMBOLS[commodity]
    period2 = int(datetime.now(UTC).timestamp())
    period1 = int((datetime.now(UTC) - timedelta(days=max(days * 2, 10))).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d"
    async with client() as http:
        response = await http.get(url)
        response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    points = [
        {
            "date": datetime.fromtimestamp(ts, UTC).date().isoformat(),
            "close": round(float(close), 4),
        }
        for ts, close in zip(timestamps, closes, strict=False)
        if close is not None
    ][-days:]
    return points, url, f"{label}; {unit}"


async def get_trend_data(commodity: str, days: int = 30) -> dict:
    commodity = commodity.lower()
    days = max(2, min(days, 365))
    if commodity not in SYMBOLS:
        return envelope(
            {},
            source_url=None,
            data_status="unavailable",
            error=f"Unsupported commodity: {commodity}. Supported values: {', '.join(SYMBOLS)}.",
        )
    _, unit, label = SYMBOLS[commodity]
    if offline_mode():
        points = _demo_points(commodity, days)
        return envelope(
            {
                "commodity": commodity,
                "instrument": label,
                "unit": unit,
                "points": points,
                "trend": calculate_trend([p["close"] for p in points]),
            },
            source_url=None,
            data_status="demo",
            error="Outbound requests disabled by MINING_AGENT_OFFLINE.",
        )
    try:
        points, url, description = await _live_points(commodity, days)
        return envelope(
            {
                "commodity": commodity,
                "instrument": description,
                "unit": unit,
                "points": points,
                "trend": calculate_trend([p["close"] for p in points]),
            },
            source_url=url,
            data_status="live",
        )
    except Exception as exc:
        return envelope(
            {},
            source_url=None,
            data_status="unavailable",
            error=f"Live market proxy unavailable: {exc}",
        )


async def get_price_data(commodity: str, on_date: str | None = None) -> dict:
    result = await get_trend_data(commodity, 30)
    if result["data_status"] == "unavailable":
        return result
    points = result["data"]["points"]
    try:
        requested = date.fromisoformat(on_date).isoformat() if on_date else date.today().isoformat()
    except ValueError:
        return envelope(
            {},
            source_url=result.get("source_url"),
            data_status="unavailable",
            error=f"Invalid ISO date: {on_date}",
        )
    eligible = [point for point in points if point["date"] <= requested]
    if not eligible:
        return envelope(
            {},
            source_url=result.get("source_url"),
            data_status="unavailable",
            error=f"No price observation is available on or before {requested}.",
        )
    point = eligible[-1]
    result["data"] = {
        "commodity": commodity.lower(),
        "requested_date": requested,
        "observation": point,
        "instrument": result["data"]["instrument"],
        "unit": result["data"]["unit"],
    }
    return result
