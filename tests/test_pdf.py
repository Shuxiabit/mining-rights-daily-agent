from mineral_pdf_mcp.service import calculate_contained_metal, extract_resource_rows


def test_extracts_indicated_and_inferred_rows_with_pages():
    pages = [
        "Mineral Resources Indicated 214 Mt at 1.32% Li2O. Notes follow.",
        "Inferred 43.5 million tonnes grading 1.21 % Li2O.",
    ]
    rows = extract_resource_rows(pages)
    assert rows[0]["classification"] == "Indicated"
    assert rows[0]["ore_tonnage_mt"] == 214
    assert rows[0]["contained_metal"] == 2.8248
    assert rows[0]["metal_unit"] == "Mt Li2O"
    assert rows[0]["page"] == 1
    assert rows[1]["classification"] == "Inferred"
    assert rows[1]["page"] == 2


def test_calculates_gold_ounces():
    value, unit = calculate_contained_metal(1.0, 2.0, "g/t Au")
    assert value == 64301
    assert unit == "oz Au"


async def test_live_pdf_failure_does_not_return_demo(monkeypatch):
    async def fail(*args, **kwargs):
        raise ValueError("blocked")

    monkeypatch.delenv("MINING_AGENT_OFFLINE", raising=False)
    monkeypatch.setattr("mineral_pdf_mcp.service.fetch_public", fail)
    from mineral_pdf_mcp.service import extract_resources

    result = await extract_resources("https://example.com/report.pdf")
    assert result["data_status"] == "unavailable"
    assert result["data"] == []
