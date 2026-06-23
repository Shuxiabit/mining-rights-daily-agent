from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from common.models import utc_now
from lme_price_mcp.service import get_trend_data
from mineral_pdf_mcp.service import extract_resources
from mining_news_mcp.service import fetch_article, search_news


@dataclass
class BriefContext:
    subject: str
    news: dict[str, Any]
    resources: dict[str, Any]
    prices: dict[str, Any]
    generated_at: str = field(default_factory=utc_now)


def infer_subject(prompt: str) -> str:
    cleaned = re.sub(
        r"(给我|生成|一份|关于|今日|日报|简报|please|create|daily|brief)", " ", prompt, flags=re.I
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" 的，,。.!?")
    return cleaned or "Pilbara 锂矿"


def infer_commodity(subject: str) -> str:
    lowered = subject.lower()
    if "copper" in lowered or "铜" in lowered:
        return "copper"
    if "nickel" in lowered or "镍" in lowered:
        return "nickel"
    if "zinc" in lowered or "锌" in lowered:
        return "zinc"
    return "lithium"


def dedupe_sources(context: BriefContext) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in context.news.get("data", []):
        url = item.get("url")
        if url and url not in seen:
            sources.append({"label": item.get("title", "Mining news"), "url": url})
            seen.add(url)
    for label, response in (("Mineral report", context.resources), ("Market data", context.prices)):
        url = response.get("source_url")
        if url and url not in seen and not url.startswith("demo://"):
            sources.append({"label": label, "url": url})
            seen.add(url)
    return sources


def _status_badge(response: dict[str, Any]) -> str:
    status = str(response.get("data_status", "unknown"))
    return {"live": "LIVE", "demo": "DEMO", "unavailable": "UNAVAILABLE"}.get(status, "UNKNOWN")


def render_offline(context: BriefContext) -> str:
    news_items = context.news.get("data", [])
    resources = context.resources.get("data", [])
    price_data = context.prices.get("data", {})
    trend = price_data.get("trend", {})
    sources = dedupe_sources(context)

    lines = [
        f"# {context.subject}矿权日报",
        "",
        f"> 生成时间（UTC）：{context.generated_at}",
        "> 数据状态说明：LIVE 为实时公开数据；DEMO 为明确标注的演示/兜底数据，不应视为投资事实。",
        "",
        "## 1. 新闻摘要",
        f"数据状态：**{_status_badge(context.news)}**",
        "",
    ]
    if news_items:
        for item in news_items[:5]:
            summary = item.get("article_excerpt") or item.get("summary", "无摘要")
            lines.append(f"- [{item['title']}]({item['url']}) — {summary}")
    else:
        lines.append("- 未检索到可用新闻。")

    lines.extend(["", "## 2. 储量数据", f"数据状态：**{_status_badge(context.resources)}**", ""])
    if resources:
        lines.extend(
            [
                "| 分类 | 矿石量 (Mt) | 品位 | 金属量 | 页码 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in resources:
            grade = f"{row.get('grade', '—')} {row.get('grade_unit') or ''}".strip()
            metal = (
                f"{row['contained_metal']} {row.get('metal_unit') or ''}".strip()
                if row.get("contained_metal") is not None
                else "未抽取"
            )
            classification = row.get("classification")
            tonnage = row.get("ore_tonnage_mt")
            page = row.get("page")
            lines.append(f"| {classification} | {tonnage} | {grade} | {metal} | {page} |")
    else:
        lines.append("未能可靠抽取资源量，建议人工复核原始报告。")

    lines.extend(["", "## 3. 价格走势", f"数据状态：**{_status_badge(context.prices)}**", ""])
    if trend:
        instrument = price_data.get("instrument")
        start, end = trend.get("start"), trend.get("end")
        unit, change = price_data.get("unit", ""), trend.get("change_pct")
        direction = trend.get("direction")
        lines.append(
            f"- {instrument}：区间从 {start} 变为 {end} {unit}，"
            f"变化 {change}%，方向为 **{direction}**。"
        )
    else:
        lines.append("- 无可用价格序列。")

    risks = [
        "价格代理风险：部分金属缺少免费、稳定的现货接口，系统会明确披露所用期货或 ETF 代理。",
        "资源量口径风险：自动抽取可能遗漏表头、单位或脚注，"
        "任何 DEMO/UNAVAILABLE 结果必须人工核验。",
        "项目执行风险：审批、融资、品位变化和建设进度均可能改变项目经济性。",
    ]
    if any(
        item.get("data_status") != "live"
        for item in (context.news, context.resources, context.prices)
    ):
        risks.insert(0, "数据完整性风险：本简报包含非实时数据，只适合演示工作流。")
    lines.extend(["", "## 4. 风险提示", "", *[f"- {risk}" for risk in risks]])

    lines.extend(["", "## 5. 引用源", ""])
    if sources:
        lines.extend(f"- [{source['label']}]({source['url']})" for source in sources)
    else:
        lines.append("- 当前为全离线演示，未使用可验证的实时外部来源。")

    for name, response in (
        ("新闻", context.news),
        ("储量", context.resources),
        ("价格", context.prices),
    ):
        if response.get("error"):
            lines.append(f"- {name}说明：{response['error']}")
    return "\n".join(lines) + "\n"


async def render_with_openai(context: BriefContext) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    payload = {
        "subject": context.subject,
        "news": context.news,
        "resources": context.resources,
        "prices": context.prices,
        "sources": dedupe_sources(context),
        "generated_at": context.generated_at,
    }
    response = await client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "你是谨慎的矿业研究助理。仅使用输入 JSON。输出中文 Markdown，必须包含新闻摘要、"
            "储量数据、价格走势、风险提示、引用源五部分。保留 LIVE/DEMO/UNAVAILABLE 状态，"
            "不得把 DEMO 数据描述成实时事实，不得编造 URL。"
        ),
        input=json.dumps(payload, ensure_ascii=False),
    )
    return response.output_text


async def _enrich_news_direct(news: dict[str, Any]) -> dict[str, Any]:
    items = news.get("data", [])
    if not items:
        return news
    details = await asyncio.gather(*(fetch_article(item["url"]) for item in items[:3]))
    for item, detail in zip(items, details, strict=True):
        text = detail.get("data", {}).get("text", "")
        if text:
            item["article_excerpt"] = text[:600]
            item["article_status"] = detail.get("data_status")
    return news


def _tool_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured.get("result", structured)
    for content in getattr(result, "content", []):
        text = getattr(content, "text", None)
        if text:
            parsed = json.loads(text)
            return parsed.get("result", parsed) if isinstance(parsed, dict) else parsed
    raise ValueError("MCP tool returned no JSON payload")


async def _call_server(module: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        return _tool_payload(await session.call_tool(tool, arguments=arguments))


async def _enrich_news_mcp(news: dict[str, Any]) -> dict[str, Any]:
    items = news.get("data", [])
    if not items:
        return news
    details = await asyncio.gather(
        *(
            _call_server("mining_news_mcp.server", "fetch_article", {"url": item["url"]})
            for item in items[:3]
        )
    )
    for item, detail in zip(items, details, strict=True):
        text = detail.get("data", {}).get("text", "")
        if text:
            item["article_excerpt"] = text[:600]
            item["article_status"] = detail.get("data_status")
    return news


async def collect_context_mcp(
    subject: str, pdf_url: str = "demo://pilbara-resource-report"
) -> BriefContext:
    commodity = infer_commodity(subject)
    news, resources, prices = await asyncio.gather(
        _call_server("mining_news_mcp.server", "search", {"query": subject, "days": 7}),
        _call_server("mineral_pdf_mcp.server", "extract_resources", {"pdf_url": pdf_url}),
        _call_server("lme_price_mcp.server", "get_trend", {"commodity": commodity, "days": 30}),
    )
    news = await _enrich_news_mcp(news)
    return BriefContext(subject, news, resources, prices)


async def collect_context_direct(
    subject: str, pdf_url: str = "demo://pilbara-resource-report"
) -> BriefContext:
    commodity = infer_commodity(subject)
    news, resources, prices = await asyncio.gather(
        search_news(subject, 7),
        extract_resources(pdf_url),
        get_trend_data(commodity, 30),
    )
    news = await _enrich_news_direct(news)
    return BriefContext(subject, news, resources, prices)


async def generate_brief(
    prompt: str,
    *,
    pdf_url: str = "demo://pilbara-resource-report",
    direct: bool = False,
) -> str:
    subject = infer_subject(prompt)
    context = (
        await collect_context_direct(subject, pdf_url)
        if direct
        else await collect_context_mcp(subject, pdf_url)
    )
    if os.getenv("OPENAI_API_KEY"):
        try:
            return await render_with_openai(context)
        except Exception as exc:
            fallback = render_offline(context)
            return fallback + f"\n> LLM 调用失败，已降级为确定性渲染：{exc}\n"
    return render_offline(context)
