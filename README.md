# unsloth-laya

**Call the local Laya decision model from any agent in one line** — turn text into calibrated, structured decisions (yes/no probability, multi-way classification, scored urgency) for ticket routing, comment triage, email filtering and content moderation. Zero dependencies, no MCP, no extra model downloads: it just talks to the [Unsloth Studio](https://unsloth.ai) Decision API running on your machine.

Laya is a **decision model**, not a chat model: it never generates text — it returns calibrated probabilities for each question you ask, which is exactly what you want for deterministic automation. Official docs: [Run Decision Models Locally with Unsloth](https://unsloth.ai/docs/models/decision-laya) ([中文](https://unsloth.ai/docs/zh/mo-xing/decision-laya)).

## How it works

```
Your agent (Hermes / Claude Code / any script)
        |  HTTP POST /v1/systemone   (Authorization: Bearer <your-local-key>)
        v
Unsloth Studio on your machine (default 127.0.0.1:8888)
        |  auto-loads & keeps Laya resident (678 MB, GPU or CPU)
        v
Calibrated structured decision JSON
```

## Install

### Into Hermes (as a skill)

Copy this `unsloth-laya/` folder into the Hermes skills directory:

```
Windows:  %LOCALAPPDATA%\hermes\skills\unsloth-laya\
Linux/macOS: ~/.hermes/skills/unsloth-laya/
```

Hermes then auto-triggers it whenever you mention "laya / 决策模型 / decision model / systemone".

### Into any other agent, or standalone

No skill install needed — `scripts/laya_client.py` is a standalone script (Python 3.8+, pure standard library). Any agent (Claude Code, Codex, OpenClaw, ...) or plain script can call it directly.

## Setup (2 minutes)

1. In Unsloth Studio go to **Settings → API → Decision API** and turn on **Serve requests** (first time downloads the 678 MB Laya model).
2. On the same page, generate a key under **Access tokens**.
3. Provide the key either via
   - env vars: `UNSLOTH_API_KEY` (and optionally `UNSLOTH_LAYA_URL`), or
   - config file: copy `templates/config.example.json` to `~/.unsloth-laya/config.json` and fill in the key.

The key lives only in your local config — **never commit it**.

## Quick test

```bash
python scripts/laya_client.py --check
# OK: Unsloth Studio reachable at http://127.0.0.1:8888; 7 models listed.

python scripts/laya_client.py --state "Hi, I was charged twice for my March invoice (#4411)." \
  --questions '{"refund": {"type": "noul", "instructions": "Does the customer ask for a refund?"}}' --pretty
```

Or as a Python module:

```python
import sys; sys.path.insert(0, "scripts")
from laya_client import ask

result = ask(state="支持工单文本…", questions={
    "refund":  {"type": "noul",  "instructions": "客户是否要求退款？"},
    "urgency": {"type": "score", "instructions": "这有多紧急？",
                 "criteria": ["不紧急", "尽快", "今天"]},
})
print(result["answers"])
```

## The three question types

| type | for | returns |
|---|---|---|
| `noul` | yes/no | probability of "yes" |
| `choice` | multi-way pick | per-option `probabilities` + `confidence` |
| `score` | graded scale | numeric `score` + per-level `probabilities` |

**Golden rule: threshold on `probabilities`, never on `confidence`** (Laya's confidence formula differs from Jev's; Jev-tuned thresholds don't transfer). See `references/api.md`.

## Real test results (measured on a local GPU instance, 2026-10)

| Scenario | Input | Output (probabilities) |
|---|---|---|
| Ticket routing (中文工单) | “嗨，我的3月发票（#4411）被重复扣费了。请今天退还多收的那一笔。” | team=billing **1.00**, refund **0.996**, urgency 1.48/2 (“今天” 0.56) |
| E-commerce review (中文差评) | “买了三次了，这次充电线用了一周就断了…客服两天了都不回，要求退货！” | negative **0.9996**, quality-issue 0.75, repurchase-intent 0.01 |
| Urgent work email (EN) | "our production server has been down for 2 hours and customers cannot check out" | priority **2.67/3 (ASAP 0.74)**, category=work **0.96** |
| Edge case (灰区) | 带剧透的夸夸评论 | pin 0.52 / review 0.33 → correctly lands in the 0.4–0.8 human-review band |

Latency: ~90 ms per request once the model is resident.

**Known caveat**: `noul` phrasing is sensitive — e.g. "Does this email need a reply?" scored 0.001 for an obviously reply-worthy outage mail. When a yes/no matters, phrase it explicitly and verify against a few samples before automating. Thresholds in `references/recipes.md` are starting points, tune them on your data.

## Repo layout

```
unsloth-laya/
├── SKILL.md                    # Hermes skill definition (triggers, workflow, rules)
├── scripts/laya_client.py      # zero-dependency client (CLI + importable ask())
├── references/api.md           # endpoint, auth, schema, limits, error table
├── references/recipes.md       # 5 ready-made question packs
└── templates/config.example.json
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Connection refused | Start Unsloth Studio |
| Not authenticated | Regenerate the key, update `~/.unsloth-laya/config.json` |
| 404 / no such route | Settings → API → Decision API → enable Serve requests |
| First request very slow | Cold model load — normal; it stays resident afterwards |

## 中文说明

在 Hermes 里一句话调用本机 Laya 决策模型——把文本变成带校准概率的结构化决策（是否/多选一/打分），用于工单路由、评论筛选、邮件过滤、内容审核。零依赖、不需要 MCP、不需要额外下载模型，只要机器上跑着 Unsloth Studio 并开启 Decision API。安装、配置、用法见上文英文部分；5 个现成问题包见 `references/recipes.md`。

## License

MIT for the scripts and docs in this repo. Laya and Unsloth Studio follow their own Unsloth AI licenses.

This is not an official Unsloth AI project — just a thin bridge that calls the local Decision API.
