# Persistent Business Memory Skill

Version: 1.0
Inspired by persistent-memory and context-database patterns, adapted to Supabase as the canonical store.

## Goal
Give agency agents cross-session business memory without introducing a second operational database.

## Memory classes
1. identity: stable business facts, market, products, brand, audiences.
2. preference: approved tone, design rules, tools, constraints.
3. decision: chosen strategies, rejected options and rationale.
4. episodic: compact summaries of completed missions and outcomes.
5. evidence: source-backed facts with freshness and provenance.
6. procedural: reusable winning/losing patterns for a specific business context.

## Write policy
Store only durable, useful information.
Never store passwords, raw API keys, secrets, private chain-of-thought or unnecessary personal data.
Each memory item requires:
- owner / business scope
- type
- title
- compact content
- source/provenance
- confidence
- freshness timestamp
- tags
- optional related mission/run
- status: active, superseded, disputed, expired

## Retrieval
Retrieve in layers:
L0: titles + one-line summaries.
L1: compact relevant memories.
L2: full content only for selected items.

Use scope before similarity:
business -> project -> capability -> time -> semantic/keyword relevance.

## Conflict handling
Never silently overwrite contradictory memories.
Create a new memory, mark conflict, preserve provenance, and let a decision/evidence agent resolve it.

## Compression
At the end of a mission:
- extract durable facts
- extract explicit decisions
- extract measurable outcomes
- extract lessons
- discard transient chatter

## Context budget
Prefer 5-12 high-value memories over large history dumps.
Summaries must preserve source links/IDs and confidence.

## Supabase
Supabase is source of truth for this agency stack. External memory frameworks are references, not required runtime dependencies.
