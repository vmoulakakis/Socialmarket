# AFFINITY Creative Production / Page Engine — Canonical Index

Status: CANONICAL
Version: 2.0
Updated: 2026-09-07

This directory contains the governed creative/page-generation layer used by AFFINITY and GrowthOps.

## Authority / precedence
When two documents appear to overlap, apply them in this order:

1. `skills/AFFINITY_SKILL.md` — commercial truth, hard gates, affiliate integrity, market/evidence authority.
2. `config/affinity-page-engine.json` — authoritative executable pipeline, scoring thresholds, page-length policy, barrier map, performance/accessibility targets and learning dimensions.
3. `skills/AFFINITY_PAGE_ENGINE.md` — page-generation strategy and vendor-pattern synthesis.
4. `PROMPT_CONTRACTS.md` — strict stage/agent input-output contracts.
5. `COMPONENT_REGISTRY.md` — canonical component IDs and functional grammar.
6. `PAGE_DNA.schema.json` — page strategy/composition object.
7. `BUILD_HANDOFF.schema.json` — deterministic builder implementation contract.
8. `EXPERIMENT.schema.json` — controlled parent/variant testing contract.
9. `QA_GATES.md` — production acceptance and rendered-page QA.
10. `SKILL.md` — creative implementation/art direction/copy/media execution policy.

Growth orchestration authority remains `agents/skills/growth-orchestrator/SKILL.md`.

## Canonical production flow

`SOURCE INGEST → CONTEXT BRIEF → BRAND/STORE DNA → DECISION BARRIERS → ANGLE MATRIX → MESSAGE MATCH → ARCHETYPE → LAYOUT DNA → PAGE DNA → COMPONENT PLAN → COPY → MEDIA → DESIGN TOKENS → BUILD → RESPONSIVE QA → CONVERSION LAYER → LOCALIZATION → CONTROLLED VARIANTS → PUBLISH → MEASURE → LEARN`

A material commercial page must not bypass this flow with an unconstrained one-shot generation prompt.

## Runtime artifacts
A serious page build should produce or be able to reconstruct:
- source packet
- context brief
- Brand/Store DNA
- decision-barrier map
- angle matrix + selected angle ID
- message-match object
- archetype decision
- reusable/versioned Layout DNA
- Page DNA
- scored component plan
- component-level copy
- asset manifest with provenance/fidelity
- design tokens
- Build Handoff object
- QA result
- experiment object when variant testing is active
- deployment/rollback reference
- analytics/learning record.

## PagePilot.ai synthesis
Public PagePilot methods integrated as abstract patterns include:
- product/source URL ingestion
- optional angle selection
- reusable/editable/duplicable layouts
- modular product blocks and sections
- drag/reorder/add/remove editing model
- inline copy/image/style editing
- brand matching
- separate responsive controls
- niche-oriented templates
- AI product image generation
- structured product descriptions
- ad copy + matching creative generation
- localized rewrites
- cart drawer, upsell/cross-sell and shipping-threshold concepts for owned commerce
- Shopify publish workflow.

The registry contains every PagePilot block/section name publicly verified in the research pass plus original AFFINITY functional equivalents. PagePilot publicly describes 35+ CRO sections/blocks and a 50+ component visual library, but does not publicly enumerate its full private inventory. Never claim undisclosed vendor internals as known.

## Magnetic.ai synthesis
Public Magnetic methods integrated as abstract patterns include:
- audience + painful problem + offer + quick win briefing
- document/context/research input
- analyze → outline → copy → images → layout stages
- message-matched pages by ad angle/audience/funnel stage
- checklists, playbooks, mini-guides and resource-list formats
- personalized sales follow-up pages
- link-in-bio/campaign resource formats
- editable drafts
- duplicate/remix/reuse model
- hosted/shareable assets
- PDF/PNG/HTML export concepts.

Magnetic does not publish a full internal component manifest. AFFINITY therefore models its public formats with original components instead of pretending private component names are known.

## Component model
The current registry contains 201 unique component/format/primitive IDs as validated by CI.

A component is not selected because it “looks good.” It is selected by conditional fit across:
- objective
- awareness stage
- decision barrier
- evidence readiness
- media readiness
- mobile behavior
- performance cost
- brand fit
- traffic source.

Default recommended component score: >=70/100.

No component is universally high converting. Learning is conditional on product × offer × audience × traffic × awareness × angle × archetype × component sequence × locale/device.

## Page-length model
Sections require a job. Default primary-section ranges:
- impulse: 5–8
- considered: 7–11
- high-ticket considered: 9–14
- professional procurement: 9–15
- lead generation: 4–9.

Longer is permitted only when additional sections resolve additional material barriers or deliver promised content value. Repetition is not a reason for length.

## Brand/Store DNA
Pages inherit a persistent brand system by default:
- voice
- visual personality
- colors
- typography character
- logo usage
- image/icon style
- radius/surfaces/shadows
- CTA rule
- motion rule
- content density
- layout rhythm
- locale rules.

A page should not invent a new visual identity unless that change is the explicit creative/experiment hypothesis.

## Layout DNA
Strong page structures are persistent/versioned assets, not disposable generations.

Layout DNA supports:
- create
- duplicate
- rename
- set default
- version
- retire.

Never silently mutate a shared winning layout used by live pages. Duplicate/version first.

## Media truth
Asset source priority:
1. user-supplied
2. verified manufacturer/merchant
3. licensed/owned
4. reference-conditioned generation
5. contextual generation.

Generated media cannot become synthetic documentary proof. Exact product controls, ports, accessories, dimensions, safety configuration, certifications and before/after results require truthful source/fidelity handling.

## Production quality
Default release requirements:
- QA score >=85/100
- zero hard failures
- correct offer/destination/tracking
- product-media fidelity pass
- responsive review at 360/390/768/1024/1440/1920 px
- WCAG 2.2 AA target
- Core Web Vitals good goals: LCP <=2.5s, INP <=200ms, CLS <=0.1 at p75 where field data exists
- experiment/analytics instrumentation where applicable
- rollback reference.

## Automated contract validation
Run:

```bash
npm run test:affinity-page-engine
```

The CI workflow `.github/workflows/affinity-page-engine-ci.yml` protects Page Engine contract changes on `main` and pull requests.

The validator checks required files, JSON parseability, pipeline stages, Page DNA fixture, component-ID uniqueness/coverage, key thresholds and orchestration dependencies.

## Vendor/IP boundary
PagePilot.ai and Magnetic.ai are research references, not code dependencies.

Allowed:
- learn from publicly documented workflow concepts
- abstract section roles and conversion mechanics
- create original implementations of useful functional patterns.

Not allowed:
- copy proprietary source code
- copy private templates
- claim undocumented private components were discovered
- clone exact protected designs/brand identities as the AFFINITY component library.

## Final operating principle
**Verified context → decision barriers → angle → message match → archetype → reusable Layout DNA → Page DNA → scored components → constrained copy/media → deterministic build → rendered QA → controlled experiments → RPV learning.**

That is the canonical AFFINITY page-production system.
