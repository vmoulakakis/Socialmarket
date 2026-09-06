# SocialMarket GrowthOps Project

Status: CANONICAL
Created: 2026-09-06
Updated: 2026-09-07

## Purpose
Persistent project reference for the autonomous GrowthOps operating model defined in the planning conversation.

## Core architecture
PUBLIC SITES → Web Analytics → Supabase ← Conversion CSV ← SocialMarket Greek Demand Brain → Growth Orchestrator → Specialist Agents → AFFINITY / Creative Production → AFFINITY Page Engine / Component Registry / Page DNA → MyAgenticTeam → GitHub / Vercel / connected site adapters → Production Verification → Supabase Learning → SocialMarket AI Admin.

## Canonical sources
- `agents/skills/growth-orchestrator/SKILL.md`
- `docs/GROWTHOPS_FINAL_REFERENCE.md`
- `skills/AFFINITY_SKILL.md`
- `skills/AFFINITY_PAGE_ENGINE.md`
- `agents/skills/affinity-creative-production/SKILL.md`
- `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md`
- `agents/skills/affinity-creative-production/PAGE_DNA.schema.json`
- `agents/skills/demand-intelligence-v3/SKILL.md`
- `agents/skills/greece-market-intelligence/SKILL.md`
- `agents/skills/competition-gap/SKILL.md`
- MyAgenticTeam repo: `vmoulakakis/Myagenticteam/GROWTHOPS_INTEGRATION.md`

## Operating rules
- Supabase is the operational source of truth.
- SocialMarket canonical intelligence is the Greek demand/competition/pain market-truth source.
- SocialMarket AI Admin is the only routine control/status surface.
- `Daily GrowthOps` is the single AI orchestration loop.
- SocialMarket AI and SocialScheduler are infrastructure, not optimization targets.
- Default autonomy is **EXECUTE, NOT ASK**.
- Perform all routine fixes, GitHub edits, Supabase repairs, SEO/CRO/content improvements, safe experiments, deployments, retries, verification and rollback autonomously whenever connected tools allow.
- Contact the user only for a new cost or a genuine user-only blocker that cannot be executed through available permissions/adapters.
- No routine completion emails and no intermediate emails; routine status goes to SocialMarket AI Admin/Supabase.

## Daily loop
Collect → Validate → Map Market Intent → Diagnose → Prioritize → Delegate → Execute → Deploy → Verify → Measure → Learn.

## Creation standard
Every new or materially revised landing page, mini-site, article/post, comparison page or creative asset must use canonical demand/pain/competition context, AFFINITY funnel logic, AFFINITY Creative Production art direction, and—when the output is a page or page-like campaign asset—the canonical AFFINITY Page Engine workflow.

For new/materially rebuilt pages the default production sequence is:
`SOURCE INGEST → CONTEXT BRIEF → ANGLE MATRIX → MESSAGE MATCH → ARCHETYPE → PAGE DNA → COMPONENT PLAN → COPY → MEDIA → DESIGN TOKENS → ASSEMBLY → RESPONSIVE QA → CONVERSION LAYER → LOCALIZATION → VARIANTS → PUBLISH → MEASURE`.

Page construction must prefer components from `COMPONENT_REGISTRY.md`, validate against `PAGE_DNA.schema.json` where structured generation is supported, use the best-fit modern framework for the existing project, remain performance-first and accessible, preserve verified claims, and include conversion instrumentation. Vendor-derived PagePilot/Magnetic patterns are used as abstract production techniques only; never copy proprietary code or exact designs.

## Duplicate prevention
- Standalone Daily Public SEO: disabled.
- Standalone Conversion Optimization: disabled.
- Standalone Affiliate Campaign Review: disabled; Monday comparison folded into GrowthOps.
- Supabase cron owns deterministic workers/data preparation, not AI decisions.
- GitHub Actions own specialized compute/publishing.
- Duplicate SocialScheduler auto-heal/feedback schedules were removed where AI autopilot already performs them.
- Weekly SocialScheduler optimization has one automatic path; duplicate GitHub schedule is manual-only.

## Outcomes
Every material experiment/change is measured and classified as KEEP / ITERATE / ROLLBACK.
