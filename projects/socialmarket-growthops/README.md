# SocialMarket GrowthOps Project

Status: CANONICAL
Created: 2026-09-06
Updated: 2026-09-07

## Purpose
Persistent project reference for the autonomous GrowthOps operating model defined in the planning conversation.

## Core architecture
PUBLIC SITES → Web Analytics → Supabase ← Conversion CSV ← SocialMarket Greek Demand Brain → Growth Orchestrator → Specialist Agents → AFFINITY / Creative Production → AFFINITY Page Engine / Config / Prompt Contracts / Component Registry / Page DNA / Build Handoff / QA / Experiments → MyAgenticTeam → GitHub / Vercel / connected site adapters → Production Verification → Supabase Learning → SocialMarket AI Admin.

## Canonical sources
- `agents/skills/growth-orchestrator/SKILL.md`
- `docs/GROWTHOPS_FINAL_REFERENCE.md`
- `skills/AFFINITY_SKILL.md`
- `skills/AFFINITY_PAGE_ENGINE.md`
- `config/affinity-page-engine.json`
- `agents/skills/affinity-creative-production/SKILL.md`
- `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md`
- `agents/skills/affinity-creative-production/PAGE_DNA.schema.json`
- `agents/skills/affinity-creative-production/PROMPT_CONTRACTS.md`
- `agents/skills/affinity-creative-production/QA_GATES.md`
- `agents/skills/affinity-creative-production/BUILD_HANDOFF.schema.json`
- `agents/skills/affinity-creative-production/EXPERIMENT.schema.json`
- `data/affinity-page-engine-example.json`
- `scripts/validate-affinity-page-engine.mjs`
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

For new/materially rebuilt pages the production sequence is:

`SOURCE INGEST → CONTEXT BRIEF → BRAND/STORE DNA → DECISION BARRIERS → ANGLE MATRIX → MESSAGE MATCH → ARCHETYPE → LAYOUT DNA → PAGE DNA → COMPONENT PLAN → COPY → MEDIA → DESIGN TOKENS → ASSEMBLY → RESPONSIVE QA → CONVERSION LAYER → LOCALIZATION → VARIANTS → PUBLISH → MEASURE → LEARN`.

### Why the extra governed stages matter
- **Brand/Store DNA** makes pages native to the existing brand rather than isolated templates.
- **Decision Barriers** prevent bloated pages by requiring each section to resolve a real purchase/lead obstacle.
- **Layout DNA** makes strong page structures persistent, versionable, duplicable and reusable instead of one-off generations.
- **Component Scoring** selects sections by objective/evidence/mobile/performance fit rather than visual preference.
- **Build Handoff** prevents the builder from redesigning strategy during coding.
- **QA Gates** audit the rendered page, product-media fidelity, message match, accessibility, performance and tracking.
- **Experiment Schema** creates interpretable parent/variant tests and protects SEO from duplicate variants.

Page construction must prefer components from `COMPONENT_REGISTRY.md`, use structured Page DNA and Build Handoff contracts where supported, reuse the existing project stack, remain performance-first and accessible, preserve verified claims, and include conversion instrumentation.

## Vendor research synthesis
The engine incorporates publicly documented/observable PagePilot.ai techniques including source-URL ingestion, angle selection, reusable layouts, modular sections/blocks, drag/reorder/editability, brand matching, responsive controls, AI product imagery, structured description copy, ad copy/creative, cart/upsell logic, localization and Shopify publishing. It also incorporates publicly documented Magnetic.ai techniques including audience/problem/offer/quick-win context, document/research inputs, analyze→outline→copy→images→layout generation, message-matched pages, lead-magnet formats, personalized follow-up, reusable/remixable assets and hosted/exportable campaign pages.

These are abstract production techniques only. Never copy vendor proprietary code, private templates, undocumented private component inventories or exact protected designs.

## Quality standard
Material page work defaults to:
- Page Engine QA score >=85/100
- zero hard failures
- correct destination/tracking
- product-media fidelity pass
- responsive review at 360/390/768/1024/1440/1920 px
- WCAG 2.2 AA target
- Core Web Vitals good targets as performance goals: LCP <=2.5s, INP <=200ms, CLS <=0.1 at p75 where field data exists
- analytics/experiment instrumentation
- rollback reference.

Run `npm run test:affinity-page-engine` after Page Engine contract changes.

## Duplicate prevention
- Standalone Daily Public SEO: disabled.
- Standalone Conversion Optimization: disabled.
- Standalone Affiliate Campaign Review: disabled; Monday comparison folded into GrowthOps.
- Supabase cron owns deterministic workers/data preparation, not AI decisions.
- GitHub Actions own specialized compute/publishing.
- Duplicate SocialScheduler auto-heal/feedback schedules were removed where AI autopilot already performs them.
- Weekly SocialScheduler optimization has one automatic path; duplicate GitHub schedule is manual-only.

## Outcomes
Every material experiment/change is measured and classified as KEEP / ITERATE / ROLLBACK / INSUFFICIENT_DATA. Learning is conditional on product × audience × traffic × awareness × angle × archetype × component sequence × locale/device; no component is treated as universally “high converting” from one result.
