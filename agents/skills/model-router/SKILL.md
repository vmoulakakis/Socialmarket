---
name: model-router
description: Canonical SocialMarket AI model selection policy: deterministic and free/open-weight first, paid reasoning only through audited caps.
---
# Model Router

Use one routing policy across SocialMarket. Do not create task-specific provider stacks that bypass this order.

## Route order

1. **Deterministic SQL/Python/vector/RAG** — always first when the work is arithmetic, filtering, joins, ranking math, hashing, exact validation or retrieval.
2. **Local open-weight runtime** — when `LOCAL_OLLAMA_URL` is configured. Current supported runtime uses Ollama/OpenAI-compatible serving and Qwen open-weight models for bounded low-risk classification/extraction. Do not let a small local model approve final evidence-backed commercial claims on its own.
3. **GitHub Models included quota** — bounded semantic fallback through `FreeModelRouter`; paid publishers are excluded from this free route.
4. **DeepSeek** — primary paid reasoning tier for genuinely difficult research/audit. Product Research and Product Skeptic use DeepSeek V4 Pro with thinking enabled when configured.
5. **OpenAI** — emergency/high-value escalation only. It is disabled by default until an explicit model/key is configured. Use low reasoning effort and a small max-output budget unless an evaluation proves more is required.

## Paid request governance

Any DeepSeek/OpenAI call must be allowed by `ops.ai_model_policy` and reserved through `ops.reserve_remote_model_request` (or the service-role RPC compatibility wrapper). The database enforces:

- task-specific provider enablement,
- minimum complexity threshold,
- written escalation reason,
- shared monthly paid-call cap,
- a stricter OpenAI daily cap,
- usage logging.

`ENABLE_PAID_REMOTE=1` is additionally required by Python workers. Product Intelligence uses the OIDC Product Gateway and the same database policy server-side.

## Quality rules

- Never use an LLM for deterministic commission calculation or merchant joins.
- Never invent demand, reviews, social metrics, product features or evidence IDs.
- RAG evidence IDs must remain attached to the result.
- A cheaper model can preclassify, summarize or reject obvious weak candidates; it cannot bypass the Product Skeptic/Audit gate.
- Record route, provider, model, token usage when available, latency, validation result and cost estimate.
- Paid escalation is for evaluation failure/complexity, not convenience.
