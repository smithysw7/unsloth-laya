# Laya Decision API 参考（Unsloth Studio）

官方文档：https://unsloth.ai/docs/models/decision-laya（中文：/docs/zh/mo-xing/decision-laya）

## 端点与鉴权

- `POST <base>/v1/systemone`（base 默认 `http://127.0.0.1:8888`）
- Header：`Authorization: Bearer <sk-unsloth-...>`，Key 在 **Settings → API → Access tokens**。
  也可开启"无密钥 API 访问"跳过 localhost 鉴权（Settings → API）。

## 请求

```json
{
  "model": "laya",
  "state": "要判断的文本（字符串或任意 JSON）",
  "questions": {
    "<问题名>": {"type": "noul|choice|score", "instructions": "..."}
  }
}
```

- `model`：`laya` / `default` / `jev-latest`（= 设置里选的模型）；或显式 `laya-multilingual`（默认，中文友好）/ `laya-english` / `laya-typed-decisions`。
- `state`：不生成文本，只做判断。超长截尾（上下文默认 16384 tokens）。

## 三种问题类型

| type | 含义 | 额外字段 | 返回 |
|---|---|---|---|
| `noul` | 是/否 | — | `noul`: "是"的概率 0~1 |
| `choice` | 多选一 | `criteria`: `{标签: 描述}` | `choice` + `confidence` + `probabilities{标签: p}` |
| `score` | 打分 | `criteria`: `["级别0", "级别1", ...]` | `score` + `confidence` + `legend{级别: 标签}` + `probabilities` |

## 响应示例（本机实测，2026-10-08）

```json
{
  "model": "laya-multilingual",
  "answers": {
    "team": {"type": "choice", "choice": "billing", "confidence": 1.0,
      "probabilities": {"billing": 1.0, "technical": 0.0, "sales": 0.0, "other": 0.0}},
    "refund": {"type": "noul", "noul": 0.9795},
    "urgency": {"type": "score", "score": 1.9005, "confidence": 0.6982,
      "legend": {"0": "not urgent", "1": "soon", "2": "today"},
      "probabilities": {"0": 0.004, "1": 0.0914, "2": 0.9046}}
  },
  "usage": {"input_tokens": 172, "output_tokens": 0}
}
```

## 限制

- 每请求最多 **64 个问题**；choice 最多 **255 选项**（共享 token 预算，带描述的选项超过约 20 个标签会截断）；score 最多 **10 级**。
- 上下文默认 16384 tokens（Settings 可调至 65536；每 token 约 0.24 MiB 显存）。

## 阈值铁律

- **行动阈值设在 `probabilities` 上**（如 `technical > 0.8` 才报 bug；`noul > 0.8` 才触发流程）。
- **不要用 `confidence` 做阈值**：Laya 与 Jev 的 confidence 公式不同，Jev 调好的阈值不可迁移。
- 0.4~0.8 中间概率 → 人工复核，不硬选。

## 错误对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `Connection refused` | Studio 没运行 / 端口不对 | 启动 Unsloth Studio；确认端口 |
| `Not authenticated` (401) | Key 错误或已轮换 | Settings → API → Access tokens 重新生成，更新 `~/.unsloth-laya/config.json` |
| 422 / schema 错误 | questions 格式不对 | 用 `scripts/laya_client.py` 的本地校验先过一遍 |
| 响应慢/首次分钟级 | 模型冷加载（GPU 首次请求） | 正常，之后常驻；确认 device=gpu |
| 404 / 无此路由 | Decision API 未启用 | Settings → API → Decision API → Serve requests 开启 |

## 从 Jev 迁移

`pip install typesafe-sdk` + 设 `TYPESAFE_API_KEY`、`TYPESAFE_BASE_URL` 指向本地。
SDK 默认模型 `jev-latest` 自动映射到设置里选的模型。注意：confidence 公式不同（阈值改设在 probabilities 上）；choice 选项共享固定 token 预算。
