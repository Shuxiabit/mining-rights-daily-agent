# Mining Rights Daily Agent

[![CI](https://github.com/Shuxiabit/mining-rights-daily-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Shuxiabit/mining-rights-daily-agent/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-3%20servers-6f42c1.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个面向矿业研究场景的 MCP（Model Context Protocol）作品：3 个独立 MCP Server 由 1 个 Agent Client 编排，生成带数据状态和引用源的中文矿权日报。

## 为什么选择这套设计

- **可验证**：新闻、资源量、价格响应共享统一数据契约。
- **不装懂**：线上数据源失败时返回 `UNAVAILABLE`；只有显式离线模式才使用 `DEMO`。
- **可演示**：无 API Key、无外网也能跑完端到端流程。
- **可扩展**：每个数据域是独立 MCP Server，可接入 Claude Desktop、Cursor 或其他 MCP Client。
- **安全边界清晰**：外部 URL 仅允许公网 HTTP(S)，并限制重定向、内容类型和响应大小。

## 架构

```text
Natural-language request
          |
          v
     Agent Client
       /   |   \
      v    v    v
  News   PDF   Price
   MCP   MCP    MCP
      \    |    /
       cited Markdown brief
```

## MCP 工具

| Server | Tool | 说明 |
|---|---|---|
| `mining-news-mcp` | `search(query, days)` | 搜索近期公开矿业新闻 |
|  | `fetch_article(url)` | 提取公开网页正文 |
| `mineral-pdf-mcp` | `extract_resources(pdf_url)` | 抽取 Indicated/Inferred 资源量及页码证据 |
| `lme-price-mcp` | `get_price(commodity, date)` | 获取最近公开市场观测 |
|  | `get_trend(commodity, days)` | 获取序列并计算涨跌趋势 |

每个工具统一返回：

```json
{
  "data": {},
  "source_url": "https://...",
  "retrieved_at": "ISO-8601 UTC",
  "data_status": "live | demo | unavailable",
  "error": null
}
```

## 快速开始

```bash
python -m pip install uv==0.11.23
uv sync --locked --extra dev
```

`uv sync` 会自动创建 `.venv`；CLI 会自动读取项目根目录中的 `.env`。

离线确定性演示：

```bash
MINING_AGENT_OFFLINE=1 uv run python -m agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

Windows PowerShell：

```powershell
$env:MINING_AGENT_OFFLINE="1"
uv run python -m agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

完整说明见 [RUN.md](RUN.md)，样例见 [examples/pilbara-brief.md](examples/pilbara-brief.md)。

## 项目文档

| 文档 | 内容 |
|---|---|
| [运行指南](RUN.md) | Docker、本地 Python、模型配置和客户端接入 |
| [系统架构](docs/ARCHITECTURE.md) | 组件关系、数据流、可靠性与扩展方向 |
| [数据契约](docs/DATA_CONTRACT.md) | MCP 通用响应及各领域字段定义 |
| [设计决策](docs/DESIGN_DECISIONS.md) | 技术取舍、原因和已知限制 |
| [面试演示脚本](docs/DEMO_GUIDE.md) | 五分钟演示顺序与常见追问 |
| [贡献指南](CONTRIBUTING.md) | 开发、测试和提交约束 |

## 数据源与限制

- 新闻：Google News RSS 搜索公开内容，Agent 会补取前 3 条新闻正文；受限页面返回不可用。
- 资源量：`pypdf` 文本抽取与保守正则；支持从吨位和品位计算 Li2O、Cu 或 Au 金属量。
- 价格：免费公开接口通常没有稳定的锂现货数据，因此系统披露所用期货/ETF 代理，绝不将代理冒充现货。
- `DEMO` 只由 `MINING_AGENT_OFFLINE=1` 或 `demo://` 输入触发；线上异常不会自动替换成演示事实。
- 目前支持 `lithium`、`copper`、`nickel` 和 `zinc`；未知矿种会返回 `UNAVAILABLE`。

## 测试

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy agent common mining_news_mcp mineral_pdf_mcp lme_price_mcp
uv run pytest --cov
```

20 项测试覆盖新闻/PDF/价格、SSRF 与响应限制、引用去重、MCP stdio 和离线端到端简报；
当前覆盖率门槛为 70%。
GitHub Actions 还会验证 Docker Compose、构建镜像、执行容器冒烟测试和 CodeQL 扫描。
依赖通过 `uv.lock` 固定，CI 与 Docker 均以 locked 模式安装，避免解析结果漂移。

## 安全

- 密钥只通过环境变量读取，`.env` 已被 Git 忽略。
- 不绕过登录墙、验证码或付费授权。
- 外部文本只作为数据，不作为 Agent 指令。
- 公网下载会校验 DNS/IP、每次重定向、Content-Type 和最大响应大小。
- 仓库启用了 Secret Scanning、Dependabot 安全更新和 `main` 分支保护。

## License

MIT
