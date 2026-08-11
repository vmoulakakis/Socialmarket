---
name: model-router
description: Select the cheapest execution path that passes quality gates, with paid remote models as a last resort.
---
# Model Router

Use this strict route order: deterministic -> local open-weight -> GitHub Models included quota -> DeepSeek -> OpenAI.

DeepSeek/OpenAI are never selected automatically from convenience. A paid escalation requires: two prior lower-cost failures when applicable, task complexity >=0.92, a written escalation reason, ENABLE_PAID_REMOTE=1, and a successful `reserve_remote_model_request` database reservation. The reservation function enforces a shared 100-request monthly hard cap.

Record route, model, token usage when available, latency, quality result and cost. Do not trade measurable quality for token reduction; escalate only when evaluation fails.
