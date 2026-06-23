# 五分钟运行指南

## 方式 A：Docker Compose

前提：安装 Docker Desktop。

```bash
docker compose up --build
```

生成结果位于 `output/pilbara-brief.md`。首次运行可强制离线，验证不依赖任何 API Key：

```bash
MINING_AGENT_OFFLINE=1 docker compose up --build
```

PowerShell：

```powershell
$env:MINING_AGENT_OFFLINE="1"
docker compose up --build
```

## 方式 B：本地 Python

需要 Python 3.12。`uv sync` 会自动创建项目的 `.venv`，无需手动激活虚拟环境。

Windows：

```powershell
python -m pip install uv==0.11.23
uv sync --locked --extra dev
$env:MINING_AGENT_OFFLINE="1"
uv run python -m agent "给我生成一份关于 Pilbara 锂矿的今日简报"
uv run pytest
```

项目提交 `uv.lock` 固定跨平台依赖，CI 和 Docker 都会使用 `--locked` 验证。
如已安装 uv，可使用：

```powershell
uv sync --locked --extra dev
uv run pytest
```

macOS/Linux：

```bash
python -m pip install uv==0.11.23
uv sync --locked --extra dev
MINING_AGENT_OFFLINE=1 uv run python -m agent "给我生成一份关于 Pilbara 锂矿的今日简报"
uv run pytest
```

## 启用模型

复制 `.env.example` 为 `.env`，CLI 启动时会自动读取该文件。配置 `OPENAI_API_KEY`，并可选设置：

- `OPENAI_BASE_URL`：任何兼容 OpenAI API 的服务地址。
- `OPENAI_MODEL`：该服务支持的模型名。

未配置 Key 或模型调用失败时，系统自动使用确定性 Markdown 渲染器，并明确说明降级原因。

## 使用真实 PDF

```bash
uv run python -m agent "生成某铜矿今日简报" --pdf-url "https://example.org/report.pdf"
```

PDF 必须是无需登录即可下载的文本型报告。扫描件或复杂跨页表格可能返回 `UNAVAILABLE`，此时系统要求人工复核，不会伪造结果。
外部 URL 必须指向公网 HTTP(S) 资源；内网地址、异常重定向、非 PDF 类型和超过 25 MB 的文件会被拒绝。

## 在线与离线状态

- `MINING_AGENT_OFFLINE=1`：使用明确标记的内置 DEMO 数据。
- 正常在线模式：只返回成功获取的 LIVE 数据。
- 在线请求失败：返回 `UNAVAILABLE` 和错误原因，不自动替换成 DEMO 数值。
- 模型 API 失败：只降级 Markdown 写作方式，不改变工具数据状态。

## 接入 Claude Desktop / Cursor

安装项目依赖后，将 `mcp-config.json` 中的 `python` 改为 `.venv` 中 Python 的绝对路径，再把 `mcpServers` 配置复制到客户端设置中。
