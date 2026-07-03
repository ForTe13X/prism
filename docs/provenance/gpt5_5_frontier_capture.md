# GPT-5.5 browser-frontier attempt — preserved capture (responses + conversation)

> The genuine extreme-capability frontier point behind **§11e** / the PREREG "Genuine frontier point". Browser-captured (Tier-2), kept here so the recorded F1s have an auditable backing. The F1s below are **recomputed** from these captured answers + the frozen ground-truths by `backend/tests/test_gpt5_capture_provenance.py` (a tamper-evident lock — edit the answers/truths and it fails), so they ARE the §11e numbers, not a retype.

## Session metadata

- **model**: GPT-5.5 (ChatGPT web, 「极速」/fast mode = low thinking effort)
- **source**: chatgpt.com (browser UI, NOT API)
- **captured_via**: Chrome MCP browser automation — flattened prompts typed into the ProseMirror composer; JSON-code-block responses read back via screenshot
- **captured_on**: 2026-06-28
- **account**: logged-in Pro session (fast mode)
- **tier**: Tier-2 — browser-captured, one-off, NOT reproducible against a pinned model; recorded values only
- **slice**: dirt 0.6 · 4 naive seeds (ho-0..3) + 1 axiom check (ho-0)
- **prompt_transforms_at_submission**:
  - newlines flattened to spaces (the ChatGPT composer sends on Enter)
  - one mojibake DISTRACTOR per cell un-garbled (a no-impact '暂未见明显影响' news item; does NOT affect the answer)
- **no_token_counts**: the web UI exposes none ⇒ H2b (token saving) is UNMEASURED for this point (structural ⇒ inferred to hold, drawn dashed in the cockpit)
- **links**:
  - docs/PREREG_axiom_gain_frontier.md (§ Genuine frontier point — GPT-5.5)
  - docs/RESEARCH_axiom_gain.md (§11e)
- **honest_note**: This is the genuine EXTREME-capability frontier point (naive F1 0.95, highest of all models). ho-2's 0.8 is NOT a capability miss: the true shipment SHP-0008 was dirt-NULLED, and GPT-5.5 correctly REFUSED to hallucinate it (a data ceiling). It lives in docs only — NOT in the protocol matrix/fixtures (can't be reproduced offline).

## Result

- **naive mean F1 (dirt 0.6, 4 cells) = 0.95** (per-cell [1.0, 1.0, 0.8, 1.0])
- **axiom F1 (ho-0) = 1.0** ⇒ **quality gain ≈ 0.00 (naive ≈ axiom ≈ data ceiling)**

## The conversation — each cell: prompt sent → GPT-5.5 answer → ground-truth → F1

### ho-0 · naive · dirt 0.6 — F1 = **1.0**

**Prompt sent** (newlines flattened to spaces at submission; one mojibake distractor un-garbled):

```
你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。

对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。只用给定上下文,不要编造。输出 JSON:{"answer":[{"news_id":"...","shipment_ids":["..."]}]}。

【上下文】
[新闻]
- NEWS-005(第3帧):HB近日道路中断,暂未见明显影响。
- NEWS-003(第11帧):华東近日台风封港,暂未见明显影响。
- NEWS-004(第24帧):华东区近日道路中断,暂未见明显影响。
- NEWS-001(第46帧):第 46 帧前后,某港口因台风封港临时停摆,吞吐骤降。
- NEWS-002(第47帧):第 47 帧前后,某港口因道路中断临时停摆,吞吐骤降。
- NEWS-007(第50帧):华北区近日台风封港,暂未见明显影响。
- NEWS-006(第55帧):华东近日台风封港,暂未见明显影响。
- NEWS-008(第56帧):HNè¿æ¥å°é£å°æ¸¯,ææªè§ææ¾å½±åã
[运单表 · 仅延误]
- SHP-0007 仓库=WH-003 发运帧=42 状态=delayed
- SHP-0011 仓库=WH-003 发运帧=46 状态=delayed
- SHP-0023 仓库=WH-001 发运帧=47 状态=delayed
[仓库表]
- WH-001 名称=华东中心仓 区域=华东 港口=宁波港
- WH-002 名称=华南中心仓 区域=华南 港口=盐田港
- WH-003 名称=华北中心仓 区域=华北 港口=天津港
[吞吐量异常(原始信号)]
- WH-001 在第47帧吞吐量骤降
- WH-003 在第46帧吞吐量骤降
```

**GPT-5.5 answer** (verbatim, JSON code block):

```json
{
  "answer": [
    {
      "news_id": "NEWS-001",
      "shipment_ids": [
        "SHP-0007",
        "SHP-0011"
      ]
    },
    {
      "news_id": "NEWS-002",
      "shipment_ids": [
        "SHP-0023"
      ]
    }
  ]
}
```

**Ground-truth**: `{"NEWS-001": ["SHP-0007", "SHP-0011"], "NEWS-002": ["SHP-0023"]}`

### ho-1 · naive · dirt 0.6 — F1 = **1.0**

**Prompt sent** (newlines flattened to spaces at submission; one mojibake distractor un-garbled):

```
你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。

对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。只用给定上下文,不要编造。输出 JSON:{"answer":[{"news_id":"...","shipment_ids":["..."]}]}。

【上下文】
[新闻]
- NEWS-007(第4帧):HD近日道路中断,暂未见明显影响。
- NEWS-005(第10帧):华东近日道路中断,暂未见明显影响。
- NEWS-001(第19帧):第 19 帧前后,某港口因台风封港临时停摆,吞吐骤降。
- NEWS-008(第31帧):华北区近日台风封港,暂未见明显影响。
- NEWS-002(第41帧):第 41 帧前后,某港口因道路中断临时停摆,吞吐骤降。
- NEWS-003(第50帧):华北近日道路中断,暂未见明显影响。
- NEWS-006(第48帧):ååè¿æ¥éè·¯ä¸­æ­,ææªè§ææ¾å½±åã
- NEWS-004(第53帧):HB近日台风封港,暂未见明显影响。
[运单表 · 仅延误]
- SHP-0002 仓库=WH-003 发运帧=41 状态=delayed
- SHP-0006 仓库=WH-003 发运帧=38 状态=delayed
- SHP-0014 仓库=WH-003 发运帧=40 状态=delayed
- SHP-0015 仓库=WH-001 发运帧=19 状态=delayed
- SHP-0019 仓库=WH-003 发运帧=37 状态=delayed
[仓库表]
- WH-001 名称=华东中心仓 区域=华东 港口=宁波港
- WH-002 名称=华南中心仓 区域=华南 港口=盐田港
- WH-003 名称=华北中心仓 区域=华北 港口=天津港
[吞吐量异常(原始信号)]
- WH-001 在第19帧吞吐量骤降
- WH-003 在第41帧吞吐量骤降
```

**GPT-5.5 answer** (verbatim, JSON code block):

```json
{
  "answer": [
    {
      "news_id": "NEWS-001",
      "shipment_ids": [
        "SHP-0015"
      ]
    },
    {
      "news_id": "NEWS-002",
      "shipment_ids": [
        "SHP-0002",
        "SHP-0006",
        "SHP-0014",
        "SHP-0019"
      ]
    }
  ]
}
```

**Ground-truth**: `{"NEWS-001": ["SHP-0015"], "NEWS-002": ["SHP-0002", "SHP-0006", "SHP-0014", "SHP-0019"]}`

### ho-2 · naive · dirt 0.6 — F1 = **0.8**

**Prompt sent** (newlines flattened to spaces at submission; one mojibake distractor un-garbled):

```
你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。

对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。只用给定上下文,不要编造。输出 JSON:{"answer":[{"news_id":"...","shipment_ids":["..."]}]}。

【上下文】
[新闻]
- NEWS-007(第2帧):华北区近日台风封港,暂未见明显影响。
- NEWS-005(第12帧):HN近日台风封港,暂未见明显影响。
- NEWS-003(第15帧):华南区近日台风封港,暂未见明显影响。
- NEWS-006(第23帧):华北近日台风封港,暂未见明显影响。
- NEWS-004(第28帧):åååºè¿æ¥å°é£å°æ¸¯,ææªè§ææ¾å½±åã
- NEWS-001(第41帧):第 41 帧前后,某港口因台风封港临时停摆,吞吐骤降。
- NEWS-002(第50帧):第 50 帧前后,某港口因道路中断临时停摆,吞吐骤降。
- NEWS-008(第53帧):华北近日台风封港,暂未见明显影响。
[运单表 · 仅延误]
- SHP-0011 仓库=WH-003 发运帧=50 状态=delayed
- SHP-0024 仓库=WH-002 发运帧=45 状态=delayed
[仓库表]
- WH-001 名称=华东中心仓 区域=华东 港口=宁波港
- WH-002 名称=华南中心仓 区域=华南 港口=盐田港
- WH-003 名称=华北中心仓 区域=华北 港口=天津港
[吞吐量异常(原始信号)]
- WH-002 在第41帧吞吐量骤降
- WH-003 在第50帧吞吐量骤降
```

**GPT-5.5 answer** (verbatim, JSON code block):

```json
{
  "answer": [
    {
      "news_id": "NEWS-001",
      "shipment_ids": [
        "SHP-0024"
      ]
    },
    {
      "news_id": "NEWS-002",
      "shipment_ids": [
        "SHP-0011"
      ]
    }
  ]
}
```

**Ground-truth**: `{"NEWS-001": ["SHP-0008", "SHP-0024"], "NEWS-002": ["SHP-0011"]}`

### ho-3 · naive · dirt 0.6 — F1 = **1.0**

**Prompt sent** (newlines flattened to spaces at submission; one mojibake distractor un-garbled):

```
你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。

对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。只用给定上下文,不要编造。输出 JSON:{"answer":[{"news_id":"...","shipment_ids":["..."]}]}。

【上下文】
[新闻]
- NEWS-004(第6帧):华北近日台风封港,暂未见明显影响。
- NEWS-008(第20帧):HB近日道路中断,暂未见明显影响。
- NEWS-006(第23帧):HN近日道路中断,暂未见明显影响。
- NEWS-005(第35帧):华南近日道路中断,暂未见明显影响。
- NEWS-001(第40帧):第 40 帧前后,某港口因台风封港临时停摆,吞吐骤降。
- NEWS-003(第43帧):华南近日道路中断,暂未见明显影响。
- NEWS-002(第47帧):第 47 帧前后,某港口因道路中断临时停摆,吞吐骤降。
- NEWS-007(第48帧):åååºè¿æ¥éè·¯ä¸­æ­,ææªè§ææ¾å½±åã
[运单表 · 仅延误]
- SHP-0008 仓库=WH-001 发运帧=40 状态=delayed
- SHP-0011 仓库=WH-001 发运帧=40 状态=delayed
- SHP-0013 仓库=WH-001 发运帧=37 状态=delayed
- SHP-0017 仓库=WH-003 发运帧=48 状态=delayed
- SHP-0021 仓库=WH-003 发运帧=47 状态=delayed
[仓库表]
- WH-001 名称=华东中心仓 区域=华东 港口=宁波港
- WH-002 名称=华南中心仓 区域=华南 港口=盐田港
- WH-003 名称=华北中心仓 区域=华北 港口=天津港
[吞吐量异常(原始信号)]
- WH-001 在第40帧吞吐量骤降
- WH-003 在第47帧吞吐量骤降
```

**GPT-5.5 answer** (verbatim, JSON code block):

```json
{
  "answer": [
    {
      "news_id": "NEWS-001",
      "shipment_ids": [
        "SHP-0008",
        "SHP-0011",
        "SHP-0013"
      ]
    },
    {
      "news_id": "NEWS-002",
      "shipment_ids": [
        "SHP-0017",
        "SHP-0021"
      ]
    }
  ]
}
```

**Ground-truth**: `{"NEWS-001": ["SHP-0008", "SHP-0011", "SHP-0013"], "NEWS-002": ["SHP-0017", "SHP-0021"]}`

### ho-0 · axiom · dirt 0.6 — F1 = **1.0**

**Prompt sent** (newlines flattened to spaces at submission; one mojibake distractor un-garbled):

```
你是跨源数据分析助手。只依据【上下文】回答,不得编造任何 id;无法确定就不输出该条。

对每条提到港口停摆/封港/中断的新闻,列出它所导致延误的运单 id。只用给定上下文,不要编造。输出 JSON:{"answer":[{"news_id":"...","shipment_ids":["..."]}]}。

【上下文】
[已解析跨源事实 · 新闻→仓库→异常→延误运单]
- NEWS-002(第47帧)→ WH-001(华东中心仓,华东/宁波港);吞吐量异常@47;延误运单=SHP-0023
- NEWS-001(第46帧)→ WH-003(华北中心仓,华北/天津港);吞吐量异常@46;延误运单=SHP-0007,SHP-0011
```

**GPT-5.5 answer** (verbatim, JSON code block):

```json
{
  "answer": [
    {
      "news_id": "NEWS-002",
      "shipment_ids": [
        "SHP-0023"
      ]
    },
    {
      "news_id": "NEWS-001",
      "shipment_ids": [
        "SHP-0007",
        "SHP-0011"
      ]
    }
  ]
}
```

**Ground-truth**: `{"NEWS-001": ["SHP-0007", "SHP-0011"], "NEWS-002": ["SHP-0023"]}`
