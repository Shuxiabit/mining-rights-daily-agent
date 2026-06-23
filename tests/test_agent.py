from agent.orchestrator import BriefContext, dedupe_sources, generate_brief


def test_deduplicates_sources():
    context = BriefContext(
        "Pilbara",
        {
            "data": [
                {"title": "A", "url": "https://example.com/a"},
                {"title": "A duplicate", "url": "https://example.com/a"},
            ]
        },
        {"source_url": "https://example.com/report"},
        {"source_url": "https://example.com/a"},
    )
    assert [item["url"] for item in dedupe_sources(context)] == [
        "https://example.com/a",
        "https://example.com/report",
    ]


async def test_offline_end_to_end(monkeypatch):
    monkeypatch.setenv("MINING_AGENT_OFFLINE", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    brief = await generate_brief(
        "给我生成一份关于 Pilbara 锂矿的今日简报",
        direct=True,
    )
    for section in ("新闻摘要", "储量数据", "价格走势", "风险提示", "引用源"):
        assert section in brief
    assert "DEMO" in brief
    assert "不应视为投资事实" in brief
    assert "生成时间（UTC）" in brief
    assert "Demonstration record" in brief
