# SocialMarket AI — Local Model Qualification V2

**Date:** 2026-08-17  
**Workflow run:** `32002971971`  
**Benchmark:** `socialmarket-local-ai-v2`  
**Owner commission hard gate tested:** `€15`  
**Qualification rule:** `5/5 cases must pass`  
**Runtime:** local Ollama on the GitHub-hosted production-class CI runner used by this repository  
**Paid inference cost:** `$0`

## Purpose

Choose the smallest local/open-weight model that can safely enter the SocialMarket AI Task Router for bounded evidence and commercial reasoning. This is a qualification gate, not a marketing benchmark and not proof that a model is universally capable.

## Cases

1. **Grounded Greek evidence** — recognize three independent Greek consumer statements supporting the same pain while excluding merchant marketing copy.
2. **Contradiction HOLD** — refuse to validate materially conflicting measurements when no resolving evidence exists.
3. **Product-pain fit** — use only attributes causally relevant to the stated problem and avoid irrelevant/invented feature reasoning.
4. **Owner commercial hard gate** — preserve expected commission `€14.90` and reject it against the immutable owner minimum `€15.00`.
5. **Prompt-injection resistance** — extract the real Greek consumer pain while ignoring commands embedded inside untrusted evidence text.

## Results

| Model | Qualified | Passed | Pass rate | Median latency | Max latency |
|---|---|---:|---:|---:|---:|
| `qwen3.5:0.8b` | NO | 1/5 | 20% | 3,012 ms | 5,795 ms |
| `qwen3.5:2b` | NO | 2/5 | 40% | 9,218 ms | 9,940 ms |
| `qwen3.5:4b` | **YES** | **5/5** | **100%** | **16,424 ms** | **18,733 ms** |

## Decision

`qwen3.5:4b` is the **minimum qualified local production tier for Category Pain audit** among the tested models.

The 0.8B and 2B models must not be used for autonomous Category Pain validation simply because they are cheaper/faster. They failed evidence-grounding, commercial or injection-resistance requirements.

No paid provider is required for the qualified Category Pain path.

## Important scope limitation

This five-case suite proves only that 4B clears the current bounded entry gate. It does **not** prove:

- production recall across all Greek categories;
- ranking quality for Top-100 product decisions;
- creative generation quality;
- calibrated confidence across arbitrary tasks;
- superiority to every other open-weight model.

Therefore the next proof is a controlled real Category Pain production sample with deterministic persistence gates unchanged. Product Ranking remains blocked until validated semantic pain exists and its own task-specific benchmark is passed.

## Production routing rule

```text
Deterministic rules / SQL / embeddings
        ↓ unresolved bounded semantic task
Qwen3.5 4B local
        ↓ schema + evidence validation
PASS → cache + persist decision telemetry
FAIL → SAFE_HOLD
```

A larger Tier 2 model may be added later only after its own benchmark. Until then, failure of 4B is not permission to invent a result or silently call a paid provider.
