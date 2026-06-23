# MCP 数据契约

## 通用响应

所有 MCP 工具都返回同一层级结构：

```json
{
  "data": {},
  "source_url": "https://example.org/source",
  "retrieved_at": "2026-06-23T08:00:00+00:00",
  "data_status": "live",
  "error": null
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data` | object / array | 工具业务数据 |
| `source_url` | string / null | 可核验的主要来源 |
| `retrieved_at` | ISO-8601 string | UTC 获取时间 |
| `data_status` | enum | `live`、`demo`、`unavailable` |
| `error` | string / null | 降级或失败原因 |

## 状态语义

- `live`：本次从公开外部源成功获取并解析。
- `demo`：仅在显式离线模式或 `demo://` 输入下使用内置演示数据。
- `unavailable`：线上数据源、校验或解析失败；`data` 通常为空，需要人工复核。

线上异常不会自动改写为 `demo`，因此调用方可以区分“主动演示”和“真实失败”。

## 新闻记录

```json
{
  "title": "Article title",
  "url": "https://...",
  "published_at": "2026-06-23T00:00:00+00:00",
  "summary": "RSS summary",
  "article_excerpt": "Optional body excerpt from fetch_article",
  "article_status": "live | demo"
}
```

`article_excerpt` 和 `article_status` 只在正文补取成功时出现。Agent 默认补取前 3 条结果。

## 资源量记录

```json
{
  "classification": "Indicated",
  "ore_tonnage_mt": 214.0,
  "grade": 1.32,
  "grade_unit": "% Li2O",
  "contained_metal": 2.82,
  "metal_unit": "Mt Li2O",
  "page": 12,
  "evidence": "Original matched text"
}
```

当前支持：

- `% Li2O`、`% Cu`：以 `Mt` 计算金属/化合物量。
- `g/t Au`：换算为金衡盎司 `oz Au`。

单位不受支持或字段无法可靠解析时返回 `unavailable`，不以零代替缺失值。

## 价格趋势

```json
{
  "commodity": "lithium",
  "instrument": "Disclosed market proxy",
  "unit": "USD/share",
  "points": [
    {"date": "2026-06-22", "close": 40.0}
  ],
  "trend": {
    "start": 38.2,
    "end": 40.0,
    "change_pct": 4.71,
    "direction": "up"
  }
}
```

`instrument` 必须披露真实使用的交易品种或代理品种。
支持的 commodity 为 `lithium`、`copper`、`nickel`、`zinc`。未知矿种、非法日期或所请求日期之前没有观测时返回 `unavailable`。

## 简报元数据

确定性 Markdown 和模型输入均包含 `generated_at`，使用 ISO-8601 UTC 时间。
