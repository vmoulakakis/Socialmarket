---
name: socialmarket-ai-architect-orchestrator
description: SocialMarket-only application adapter for AI Architect, specialist tasks, 334 Linkwise program reconciliation, evidence learning, 384D multilingual GraphRAG and verified >=EUR10 affiliate decisions.
version: 1.0.0
reviewed: 2026-10-30
canonical_owner: vmoulakakis/Myagenticteam/skills/agent-runtime-2026
---
# SocialMarket AI Architect — VMDB application adapter

Canonical proposed upstream skill: https://github.com/vmoulakakis/Myagenticteam/blob/feat/socialmarket-hybrid-graphrag-20261030/skills/socialmarket-ai-architect-orchestrator/SKILL.md

Read this repository's AGENTS.md, agentic-development-lifecycle and data contracts.
This is an application-scoped entrypoint, not a broad license to change VMDB tenants.

## Roles, objectives and boundaries
AI Architect controls a bounded specialist queue. Merchant Identity (334 program records,
317 missing IDs); Commission Verifier (time-valid publisher approvals); Greece Demand-Supply
(41 existing pain gaps and counterevidence); Product Analyst (3,921 historical imports);
GraphRAG Librarian (384D E5 + SQL/FTS + provenanced two-hop graph);
Commercial Skeptic (independent check); Learning Analyst (attributable verified outcomes).
At most three concurrent specialist tasks; one model via current SocialMarket gateway budgets.

## Live VMDB targets
Project `gqpbskssrvpfjtujwezc`, private `sm_intel` only.
- `merchant_program_directory`: **334 program rows** and 317 missing Linkwise IDs.
  Source `active_since` is not end-of-validity; all terms `valid_to` are presently unknown.
  Never label historical mapped status as publisher approval.
- `agent_objectives`, `agent_tasks`, `agent_runs`,
  `agent_learning_observations`, `agent_change_proposals`.
- `search_documents`, `hybrid_retrieve`, `graph_context`.
- `qualified_offers` and `promotion_ready_offers` enforce
  minimum calculated commission >=EUR10, authentic tracking URL,
  current stock and verified terms, current publisher and campaign eligibility.
- Deployed Edge Function `socialmarket-architect`:
  admin-only POST action=status/run; model reasoning delegated to the
  existing budgeted `socialmarket-ai` endpoint. If evidence missing, response
  stays `needs_evidence`, not `verified`.
- Deployed Edge Function `socialmarket-graphrag`:
  admin-only query/search/reason, explicit lexical-only fallback while
  `search_documents.embedding_status='ready'` count is zero.

## Research and learning
Prioritize high-intent Greek problems with independently sourced *real* demand and
insufficient local supply. Keep source URLs, dates, regions, substitutes, rival
merchant prices, observed stock, seller trust and counterevidence. Incentives
must be factual; no fear, coercion or fake scarcity.
New model output is a hypothesis until verified; the model cannot approve
terms, change commercial policy, publish, spend or update training weights.

Tests: DB exact EUR9.99 rejected/EUR10 accepted with fixtures rolled back;
bounded batch ingestion; private RLS; GitHub Python + Deno CI;
do not claim production model usage or 3.84GB feed import without actual logs.
