# 现成问题包（Recipes）

每个包可直接存成 JSON 文件给 `scripts/laya_client.py --questions-file` 用。
规则：instructions 语言跟随输入文本语言；阈值设在 probabilities 上。

## 1. 客服工单路由（中）

```json
{
  "team": {"type": "choice", "instructions": "该由哪个团队来处理？",
    "criteria": {"billing": "发票、付款、退款", "technical": "错误、宕机、报错", "sales": "定价、新方案", "other": "其他所有内容"}},
  "refund": {"type": "noul", "instructions": "客户是否要求退款？"},
  "urgency": {"type": "score", "instructions": "这有多紧急？", "criteria": ["不紧急", "尽快", "今天"]}
}
```

本机实测（state="嗨，我的3月发票（#4411）被重复扣费了。请今天退还多收的那一笔。"）：
`team=billing(p=1.0)`, `refund=0.9958`, `urgency≈1.48`（偏"今天"）。

## 2. 电商评论分析（中）

```json
{
  "sentiment": {"type": "choice", "instructions": "评论的情感倾向？",
    "criteria": {"positive": "好评、满意、推荐", "neutral": "客观描述、无倾向", "negative": "差评、不满、投诉"}},
  "has_quality_issue": {"type": "noul", "instructions": "是否提到产品质量问题（破损/瑕疵/故障）？"},
  "mentions_logistics": {"type": "noul", "instructions": "是否提到物流问题（慢/丢件/破损）？"},
  "repurchase_intent": {"type": "noul", "instructions": "是否表达了复购或推荐意愿？"}
}
```

用法：negative 概率 > 0.8 → 转售后跟进；has_quality_issue > 0.8 → 触发质检工单。

## 3. 短剧/内容评论筛选（中）

```json
{
  "action": {"type": "choice", "instructions": "这条评论应该如何处置？",
    "criteria": {"pin": "优质、精彩、值得置顶", "keep": "正常评论", "review": "疑似引战/剧透/擦边，需人工看", "delete": "辱骂、广告、垃圾信息、明显违规"}},
  "is_ad": {"type": "noul", "instructions": "是否是广告/刷评/带外链导流？"},
  "is_spoiler": {"type": "noul", "instructions": "是否剧透关键剧情？"}
}
```

用法：delete > 0.7 → 删；review > 0.5 → 进人工队列；pin > 0.9 → 候选置顶。

## 4. 邮件过滤（英）

```json
{
  "needs_reply": {"type": "noul", "instructions": "Does this email need a reply?"},
  "priority": {"type": "score", "instructions": "How urgent is it?", "criteria": ["whenever", "this week", "today", "ASAP"]},
  "category": {"type": "choice", "instructions": "What is this email about?",
    "criteria": {"work": "tasks, projects, meetings, deadlines", "personal": "friends, family", "transactional": "receipts, notifications, automated", "spam": "marketing, cold outreach, phishing"}}
}
```

用法：needs_reply > 0.8 且 priority ≥ 2 → 当日待办；category=spam > 0.9 → 归档。

## 5. 内容审核（通用）

```json
{
  "risk": {"type": "choice", "instructions": "内容风险等级？",
    "criteria": {"safe": "正常内容", "borderline": "擦边、争议、需上下文判断", "violation": "辱骂、色情、暴力、违法"}},
  "is_spam": {"type": "noul", "instructions": "是垃圾/营销内容吗？"},
  "toxicity": {"type": "score", "instructions": "毒性强弱？", "criteria": ["无", "轻微", "强烈"]}
}
```

## 设计新问题包的规则

1. 标签用简短英文键名（好写代码），criteria 描述用目标语言。
2. 一个包聚焦一个场景，把相关问题合并进一次请求（省推理次数）。
3. 每个动作型问题先想清楚阈值再上线：>0.8 自动执行；0.4–0.8 人工复核；<0.4 放行/忽略。
4. score 的 criteria 是**从低到高**排列的级别标签。
