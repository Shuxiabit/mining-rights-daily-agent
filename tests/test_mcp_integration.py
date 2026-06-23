from agent.orchestrator import _call_server


async def test_all_mcp_servers_return_shared_contract(monkeypatch):
    monkeypatch.setenv("MINING_AGENT_OFFLINE", "1")
    calls = [
        ("mining_news_mcp.server", "search", {"query": "Pilbara lithium", "days": 7}),
        (
            "mineral_pdf_mcp.server",
            "extract_resources",
            {"pdf_url": "demo://pilbara-resource-report"},
        ),
        ("lme_price_mcp.server", "get_trend", {"commodity": "lithium", "days": 7}),
    ]
    for module, tool, arguments in calls:
        response = await _call_server(module, tool, arguments)
        assert {"data", "source_url", "retrieved_at", "data_status", "error"} <= response.keys()
        assert response["data_status"] == "demo"
