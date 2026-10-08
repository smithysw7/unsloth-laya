---
name: unsloth-laya
version: 1.0.0
description: Use when calling Laya. Bridges Unsloth local decision API.
author: qiandy
license: MIT
metadata:
  hermes:
    tags: [decision-model, unsloth, laya, api-bridge, classification]
    related_skills: []
triggers:
  - "laya"
  - "决策模型"
  - "decision model"
  - "systemone"
  - "unsloth decision"
mutating: false
---

# Laya 决策模型 via Unsloth Studio（HTTP 桥接）

把一段文本变成**带校准概率的结构化决策**：是否退款、属于哪个团队、紧急程度几分。
不是聊天模型——它不生成文本，只对问题返回概率，适合自动分类/路由/打分/过滤/审核。
桥接方式：HTTP 调用本机 Unsloth Studio 的 Decision API（`POST /v1/systemone`），
零依赖、不需要 MCP、不需要额外下载模型。

## When to Use

触发条件（任一）：
- 用户提到 laya / 决策模型 / decision model / systemone，或要求"用 laya 分类/判断/打分"。
- 需要把批量文本变成结构化决策：工单路由、评论筛选/审核、邮件过滤、打标、紧急度打分。
- 需要"是否"型概率判断或多选一分类，且要求确定性输出（不生成文本）。

不适用：生成文本/改写/摘要 → 用普通聊天模型；多轮规划决策 → 用 decision-mapping。

## Contract

- 通过 `scripts/laya_client.py`（纯标准库）发送决策请求，返回解析后的答案。
- 零依赖：Python 3.8+，不装任何包；不需要 MCP。
- 永不硬编码 API Key：从 `UNSLOTH_API_KEY`/`UNSLOTH_LAYA_URL` 环境变量或 `~/.unsloth-laya/config.json` 读取。Key 绝不写进技能文件、输出或会提交的文档。
- 行动阈值设在 `probabilities` 上，绝不用 `confidence`（与 Jev 公式不同，阈值不可迁移）。
- 请求失败给出明确诊断（Key 错误 / Studio 未启动 / 问题格式错误），重试不超过 2 次。

## 前置条件（宿主机）

1. Unsloth Studio 正在运行，且 **Settings → API → Decision API → Serve requests** 已开启（首次开启会下载 678 MB 的 Laya）。
2. 同页面 **Access tokens** 有可用 Key。
3. 默认地址 `http://127.0.0.1:8888`；改过端口以用户给的为准。

## Phases

1. **查配置与连通性**（首次或报错时）：`python scripts/laya_client.py --check`
   - connection refused → Studio 没开或端口不对；
   - Not authenticated → Key 错/已轮换，让用户重新生成并更新 `~/.unsloth-laya/config.json`。
2. **设计问题**：参考 `references/api.md` 的三种问题类型（noul/choice/score）。规则：
   - instructions 语言与输入文本一致（中文输入用中文 instructions）；
   - choice 的 criteria 是 `{标签: 描述}`，带描述选项超过约 20 个会截断；score 最多 10 级；
   - 单请求最多 64 个问题，能合并就合并（一次请求省一次推理）。
3. **调用**：优先用脚本而非裸 curl（脚本处理配置、UTF-8、本地校验）：
   `python scripts/laya_client.py --state "<文本>" --questions-file questions.json --pretty`
   现成问题包见 `references/recipes.md`（工单路由/电商评论/短剧评论筛选/邮件过滤/内容审核）。
4. **解读与行动**：阈值设在 `probabilities` 上（如 `refund.noul > 0.8` 才触发退款；`team.probabilities.technical > 0.8` 才报 bug）。0.4–0.8 输出为"人工复核"，不硬选。

## Output Format

- 结论：每个问题一行——`问题 → 答案（概率/分数）→ 建议动作`。
- 附原始 JSON（或存工作区文件）供程序化后续使用。
- 边界概率（0.4–0.8）明确标注"建议人工确认"。

## Anti-Patterns

- ❌ 用 `confidence` 做行动阈值（必须用 `probabilities`）。
- ❌ 把 API Key 写进任何会提交/开源的文件；❌ 在输出中打印 Key。
- ❌ 拿 Laya 当聊天模型用（它不生成文本；生成文本用 `/v1/chat/completions` 的普通模型）。
- ❌ 不检查连通性就盲目重试；❌ 用英文 instructions 处理中文输入（反之亦然）。
- ❌ state 塞超长文本不截断（默认上下文 16384 tokens，超长截尾）。

## Tools Used

- `terminal` / `execute_code`：运行 `scripts/laya_client.py`。

## Reference Files

- `scripts/laya_client.py` — 零依赖客户端（CLI + 可导入模块）。
- `references/api.md` — 端点、鉴权、schema、限制、错误对照表。
- `references/recipes.md` — 5 个现成问题包（含本机实测输出）。
- `references/open-source-readme.md` — 开源发布说明（Hermes / 任何 agent / 独立使用），发布时复制为仓库根 README。
- `templates/config.example.json` — 配置模板。
