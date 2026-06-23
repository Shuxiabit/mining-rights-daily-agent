from lme_price_mcp.service import calculate_trend, get_price_data, get_trend_data


def test_calculates_price_trend():
    assert calculate_trend([10, 11]) == {
        "start": 10,
        "end": 11,
        "change_pct": 10.0,
        "direction": "up",
    }
    assert calculate_trend([])["direction"] == "unknown"


async def test_unknown_commodity_is_rejected(monkeypatch):
    monkeypatch.setenv("MINING_AGENT_OFFLINE", "1")
    result = await get_trend_data("uranium")
    assert result["data_status"] == "unavailable"
    assert "Unsupported commodity" in result["error"]


async def test_historical_date_before_series_is_unavailable(monkeypatch):
    monkeypatch.setenv("MINING_AGENT_OFFLINE", "1")
    result = await get_price_data("lithium", "2000-01-01")
    assert result["data_status"] == "unavailable"
    assert result["data"] == {}


async def test_invalid_price_date_is_unavailable(monkeypatch):
    monkeypatch.setenv("MINING_AGENT_OFFLINE", "1")
    result = await get_price_data("lithium", "not-a-date")
    assert result["data_status"] == "unavailable"


async def test_live_price_failure_does_not_return_demo(monkeypatch):
    async def fail(*args, **kwargs):
        raise ValueError("blocked")

    monkeypatch.delenv("MINING_AGENT_OFFLINE", raising=False)
    monkeypatch.setattr("lme_price_mcp.service._live_points", fail)
    result = await get_trend_data("lithium")
    assert result["data_status"] == "unavailable"
    assert result["data"] == {}
