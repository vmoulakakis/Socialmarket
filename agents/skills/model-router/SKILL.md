---
name: model-router
description: Canonical SocialMarket AI model selection policy: deterministic and free/open-weight first, paid reasoning only through audited caps.
---
# Model Router

Use one routing policy across SocialMarket. Do not create task-specific provider stacks that bypass this order.

## Route order

1. **Deterministic SQL/Python/vector/RAG** — always first when the work is arithmetic, filtering, joins, ranking math, hashing, exact validation or retrieval.
2. **Local open-weight runtime** — when `LOCAL_OLLAMA_URL` is configured. Current supported runtime uses Ollama/OpenAI-compatible serving and Qwen open-weight models for bounded low-risk classification/extraction. Do not let a small local model approve final evidence-backed commercial claims on its own.
3. **Verified free tier** — Groq GPT-OSS 20B (account confirmed free), then OpenRouter `openrouter/free`; no verified credentials means fail closed/deterministic fallback. GitHub Models has been fully retired since 2026-07-30.
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

## Free-tier activation (2026-11-09)
GitHub Actions: add `GROQ_API_KEY` or `OPENROUTER_API_KEY` as encrypted repository secrets, and `GROQ_FREE_TIER_CONFIRMED=true` in repository variables after checking the account plan. To allow external free providers to process private repository source in the *code executor*, separately review privacy and set `FREE_CODE_EXTERNAL_ALLOWED=true`; default is BLOCKED. For Vercel, configure separate server-only environment variables. No API keys are created by a GitHub commit. Reference: https://github.blog/changelog/2026-07-30-github-models-is-now-retired/ .

Privacy gate: `FREE_AGENT_EXTERNAL_ALLOWED`, `FREE_CODE_EXTERNAL_ALLOWED` and `FREE_MERCHANT_EXTERNAL_ALLOWED` are separate GitHub Actions variables and remain false by default. Never send private merchant conversion metrics, source code or confidential data to external free providers merely because an API key exists. Opt in only after data review. Local Ollama remains the preferred confidentiality-preserving route.
