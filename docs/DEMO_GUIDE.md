# 面试演示脚本

建议用时：5 分钟。

## 1. 介绍目标（30 秒）

“这个项目用三个 MCP Server 聚合矿业新闻、NI 43-101 类资源量报告和价格趋势，再由 Agent 生成带引用的矿权日报。重点不是假装所有免费数据都稳定，而是对实时、演示和不可用状态做透明处理。”

## 2. 展示架构（30 秒）

打开 `docs/ARCHITECTURE.md`，说明三个数据域独立、Agent 并行编排、任一来源失败可局部降级。

## 3. 运行离线演示（1 分钟）

PowerShell：

```powershell
$env:MINING_AGENT_OFFLINE="1"
uv run python -m agent "给我生成一份关于 Pilbara 锂矿的今日简报"
```

指出 UTC 生成时间、五个固定章节和 `DEMO` 标识，并说明 DEMO 只由显式离线模式触发。

## 4. 展示 MCP 协议（1 分钟）

打开 `mcp-config.json` 和三个 `server.py`，说明相同服务可以接入 Claude Desktop、Cursor 或自定义 Client。

## 5. 展示测试（30 秒）

```powershell
uv run pytest --cov
```

说明当前有 20 项测试、覆盖率门槛 70%，覆盖 SSRF、响应大小、失败语义、日期边界、三台 MCP Server 的真实 stdio 调用和无密钥端到端流程。

## 6. 讨论生产化（1 分钟）

- PDF：表格检测、OCR、字段置信度和人工审核队列。
- 数据：授权行情、缓存和重试。
- Agent：模型交叉审核、事实引用约束和可观测性。
- 工程：展示 CI、Docker、CodeQL、Dependabot 安全更新和受保护的 `main` 分支。

## 常见追问

**为什么不用一个 Server？**

三个领域的依赖和失败模式不同，拆分后可以独立替换数据源和扩缩容。

**为什么内置演示数据？**

为了让评审稳定验证编排流程；只有显式离线模式才启用，线上故障不会自动返回演示事实。

**如何防止 MCP 工具访问内网？**

所有外部 URL 都经过公网 IP、重定向、Content-Type 和响应大小检查，拒绝 loopback、私网和 link-local 地址。

**模型会不会编造？**

模型只能读取工具返回的结构化 JSON，并被要求保留状态、禁止新增 URL；无模型时仍能确定性生成。
