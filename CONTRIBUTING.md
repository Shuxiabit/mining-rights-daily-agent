# Contributing

## Development

```bash
python -m pip install uv==0.11.23
uv sync --locked --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy agent common mining_news_mcp mineral_pdf_mcp lme_price_mcp
uv run pytest --cov
```

提交前请确保：

- 新工具继续遵守统一 MCP 数据契约。
- 演示或缓存数据明确标记为 `demo`。
- 线上失败必须返回 `unavailable`，不得自动使用演示数值。
- 新的外部 URL 访问必须复用 `common.http.fetch_public` 的安全边界。
- 修改依赖后运行 `uv lock` 并提交更新后的 `uv.lock`。
- 不提交 `.env`、访问令牌、付费数据或受限内容。
- 新行为具有相应单元或集成测试。
