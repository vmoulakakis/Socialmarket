# Growth Orchestrator Skill

Version: 2.0
Updated: 2026-09-07

## Mission
Operate a single autonomous GrowthOps control loop for all user-owned public websites, with SocialMarket AI Admin as the only control/status interface, Supabase as the source of truth, Vercel/GitHub/connected ChatGPT-site builders as execution adapters, and evidence-based optimization as the governing principle.

## Scope
Include all ACTIVE public sites registered in the Supabase site master registry, including Vercel, GitHub+Vercel and connected ChatGPT-created sites. Exclude internal/test/duplicate/archived properties and exclude SocialMarket AI and SocialScheduler as optimization targets; they are control/publishing infrastructure.

## Canonical architecture
PUBLIC SITES -> WEB ANALYTICS -> SUPABASE <- CONVERSION CSV <- SOCIALMARKET DEMAND BRAIN -> GROWTH ORCHESTRATOR -> SPECIALIST AGENTS -> AFFINITY / CREATIVE PRODUCTION -> AFFINITY PAGE ENGINE / COMPONENT REGISTRY / PAGE DNA -> DEPLOYMENT ADAPTERS -> PRODUCTION -> VERIFY -> SUPABASE LEARNING -> SOCIALMARKET AI ADMIN.

## Canonical creative/page dependencies
For any new or materially rebuilt commercial page, landing page, microsite, mini-site, comparison experience, lead magnet or campaign page, the orchestrator must route creation through:

- `skills/AFFINITY_SKILL.md` — commercial truth, funnel authority, claims/evidence, affiliate tracking and Greece/EU economics.
- `skills/AFFINITY_PAGE_ENGINE.md` — source ingestion, angle selection, message matching, archetype selection, Page DNA, controlled generation and remix/variant workflow.
- `agents/skills/affinity-creative-production/SKILL.md` — implementation/art-direction/copy/media/QA execution.
- `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md` — reusable component grammar.
- `agents/skills/affinity-creative-production/PAGE_DNA.schema.json` — machine-readable page specification.

This routing is mandatory for new/material page creation. CRO micro-edits to an existing page may remain narrowly scoped when a complete page rebuild would be disproportionate, but material structure/hero/offer/message changes must still respect the current AFFINITY angle, evidence, component and measurement rules.

## Required inputs
### Automatic web analytics per site and page
Use page/session/visitor data, landing page, referrer/source/UTM, country/device, CTA clicks, affiliate outbound clicks, key events, funnel events, errors, SEO/search metrics when available, and Core Web Vitals/performance evidence.

### Conversion CSV
Treat uploaded conversion/commission/sales CSV data as business-truth input after normalization and validation. Track freshness using last_conversion_import_at, conversion_data_until, source_filename, rows_imported, sites_covered and data_freshness_status.

Freshness states:
- FRESH: normal decision confidence.
- AGING: continue with reduced confidence.
- STALE: avoid aggressive conversion decisions; request fresh data.
- MISSING: request upload.

When conversion data is stale, missing, incomplete, unparsable or insufficient for an experiment, create a data request and send the user an email asking for an updated CSV. Do not repeatedly nag when no new data is required.

### SocialMarket Greek Demand Brain
Before prioritizing SEO, content, affiliate, product-page or market-positioning actions, consume the existing SocialMarket market-intelligence stack rather than creating a second demand model.

Canonical dependencies:
- `agents/skills/demand-intelligence-v3/SKILL.md`
- `agents/skills/greece-market-intelligence/SKILL.md`
- `agents/skills/competition-gap/SKILL.md`
- existing merchant Demand Beacon, Solution Whitespace, pain-gap and Product Opportunity intelligence governed by `agents/ORCHESTRATOR.md`.

Truth rules:
- canonical market metrics remain owned by SocialMarket production truth; GrowthOps never recalculates or overwrites canonical demand_score, competition_score, pain_gap_score, opportunity_score or confidence.
- missing demand/competition/pain values remain missing and increase uncertainty.
- observed, derived, modeled and withheld evidence must remain explicitly separated.
- Greek-market evidence is preferred for Greek opportunity decisions.
- large Greek commerce sites may act as demand beacons and must not automatically be treated as direct competition.

For each site/page whose commercial intent can be mapped to a canonical category/subcategory/product/pain theme, retrieve at minimum when available:
- Greek current demand and direction
- demand evidence quality/confidence
- retail saturation
- content saturation
- brand/merchant concentration
- authority barrier
- solution coverage gap
- validated pain-gap state
- merchant Solution Whitespace / Demand Beacon context
- seasonality/theme state
- forecast readiness / forecast state
- contradictions/falsifiers
- next evidence to collect.

If a site cannot be confidently mapped to canonical taxonomy or demand theme, mark `market_context_status=unmapped` and do not fabricate demand context.

## Master agent responsibilities
The Growth Orchestrator is the only agent that prioritizes and assigns site changes. Every daily cycle follows:
Collect -> Validate -> Map Market Intent -> Diagnose -> Prioritize -> Delegate -> Execute -> Deploy -> Verify -> Measure -> Learn.

Prevent conflicting concurrent work on one site by site-level execution locks. Specialist agents may recommend actions, but only the orchestrator promotes them into execution.

## Specialist agents
- Analytics Agent: telemetry ingestion, attribution, anomalies, data quality and conversion imports.
- Greek Demand Intelligence Agent: binds site/page intent to canonical SocialMarket demand intelligence and returns demand, whitespace, saturation, confidence, contradictions and next-evidence state without changing canonical truth.
- SEO Black Belt Agent: ranking opportunity, technical SEO, schema, crawl/indexation, search intent, internal linking and content gaps, conditioned on Greek demand/competition evidence when the site targets Greece.
- CRO Agent: CTA, affiliate CTR, conversion funnel, UX, trust, copy, page structure and experiments. For material page changes it produces the measurable hypothesis but delegates generation/implementation through AFFINITY Creative Production/Page Engine rather than free-form redesign.
- Content Agent: buyer-intent, comparison, problem/solution and pain-gap content grounded in validated demand/pain/competition evidence.
- AFFINITY Creative Production Agent: converts an approved commercial/content hypothesis into context brief, angle matrix, message-match definition, archetype, Page DNA, component plan, copy/media/design-token plan, implementation, controlled variants and page QA under `skills/AFFINITY_PAGE_ENGINE.md` and `agents/skills/affinity-creative-production/SKILL.md`.
- Research Agent: incremental evidence collection only where the SocialMarket demand brain identifies uncertainty or missing evidence; do not duplicate validated research.
- Performance Agent: Core Web Vitals, mobile UX, page weight, rendering and runtime performance.
- Link & Affiliate Agent: affiliate tracking URL integrity, outbound CTR and broken/expired destination monitoring.
- Deployment Agent: GitHub/Vercel/connected site-builder preview, production deployment, canonical production-state enforcement.
- QA/Rollback Agent: post-deployment technical and business validation; rollback on regression.
- Data Freshness Agent: CSV coverage/freshness checks and user email requests when new conversion data is needed.

## Material page-change routing
Treat the following as material and route through AFFINITY Creative Production/Page Engine:
- new landing page or microsite
- new lead magnet/campaign page
- new product page architecture
- material hero/value proposition change
- material offer/angle/audience change
- section architecture or page-length redesign
- new comparison/high-ticket/ROI/quiz/configurator experience
- substantial brand/art-direction redesign
- ad-to-landing message-match variant.

The required creation sequence is:

`SOURCE INGEST -> CONTEXT BRIEF -> ANGLE MATRIX -> MESSAGE MATCH -> ARCHETYPE -> PAGE DNA -> COMPONENT PLAN -> COPY -> MEDIA -> DESIGN TOKENS -> ASSEMBLY -> RESPONSIVE QA -> CONVERSION LAYER -> LOCALIZATION -> VARIANTS -> PUBLISH -> MEASURE`

Every major section should map to a component in `COMPONENT_REGISTRY.md` or a justified custom component. Do not permit an unconstrained “generate a beautiful landing page” implementation path for material commercial work.

## Decision model
Do not optimize every site every day. Rank opportunities using evidence and sufficient sample size.

For each site/page compute at minimum:
- Traffic Opportunity
- SEO Opportunity
- Conversion Opportunity
- Greek Demand Opportunity
- Competition / Whitespace Opportunity
- Commercial Value
- Technical Risk
- Evidence Confidence

Growth Priority Score should favor expected business lift, Greek demand strength/direction, validated whitespace/pain gap, confidence, meaningful traffic/commercial value and reversibility while penalizing saturation, authority barriers, implementation effort and risk.

Do not replace canonical SocialMarket scores with GrowthOps scoring. Growth Priority Score is an execution-priority layer only.

SEO Opportunity should reflect search demand, ranking/CTR gap, content/retail saturation, authority barrier, business value and probability of improvement.
CRO Opportunity should reflect traffic, commercial intent, conversion gap and expected lift.
Content Opportunity should require validated demand/pain or a defensible information gap; popularity alone is insufficient.
Affiliate Opportunity should combine conversion evidence with merchant economics, validated Solution Whitespace and competition context; commission alone is never enough.

Do not modify a page merely because a generic best practice exists. Require a measurable hypothesis.

## Demand-aware action policy
Examples of routing logic:
- HIGH demand + HIGH whitespace + low organic visibility -> prioritize SEO/content acquisition.
- HIGH demand + existing traffic + weak affiliate/CTA conversion -> prioritize CRO.
- HIGH demand + HIGH retail/content saturation + high authority barrier -> avoid generic head-term content; seek pain-specific or differentiated long-tail intent backed by evidence.
- RISING demand + validated seasonal/theme evidence -> accelerate time-sensitive content/landing optimization.
- LOW/uncertain demand + weak evidence -> collect evidence or wait; do not spend deployment cycles on speculative expansion.
- strong conversions but declining demand -> protect high-performing pages but avoid over-investing in expansion until demand is revalidated.
- strong demand but weak/unsafe merchant economics -> do not force affiliate promotion; separate market opportunity from monetization viability.

## Funnel model
Optimize the entire chain:
Greek demand / pain intent -> Search intent -> Landing page -> Engagement -> CTA -> Affiliate click -> Conversion/commission.

SEO must not maximize low-intent traffic at the expense of commercial outcomes. CRO must not overfit pages with insufficient traffic. Demand intelligence must not be used as a substitute for observed site conversion data.

When traffic originates from a specific ad, email, social post or campaign, treat message match as part of the funnel: source hook/problem/promise/offer must continue coherently into the landing hero and first proof sequence. Materially different angles should generally receive controlled page variants rather than one diluted generic page.

## Experiment and learning policy
Every material change must record:
- hypothesis
- target site/page
- canonical market/taxonomy mapping if applicable
- demand/competition/pain context snapshot
- selected angle and message-match state when applicable
- Page DNA / component IDs for material page work when supported
- baseline window
- target metric
- implementation reference/commit/deployment
- parent/variant relationship when applicable
- measurement window
- before metric
- after metric
- lift
- confidence
- outcome

Outcomes:
- KEEP: statistically/practically credible improvement.
- ITERATE: promising but insufficient evidence.
- ROLLBACK: technical or business regression.

Persist reusable winning/losing patterns in optimization_knowledge by site type, market state, demand state, competition state, change type, angle, page archetype, component IDs, metric lift and confidence so future actions learn from the user's own portfolio.

Never write experiment lift back into canonical demand/competition truth. Site-performance learning and market-intelligence truth remain separate but linkable.

Do not call a PagePilot/Magnetic-derived component or any AFFINITY component universally “high converting” based on one result; learn conditional fit by product × offer × audience × traffic × archetype × component sequence.

## Deployment policy
For GitHub/Vercel sites use:
AI change -> commit -> build/preview -> quality gates -> production -> health verification -> analytics confirmation.

Production gates include as applicable:
- build success
- HTTP 200 for critical routes
- no new runtime errors
- canonical/robots/sitemap valid
- affiliate links valid
- schema/metadata valid
- no material Core Web Vitals regression
- no unsupported market, demand, price, savings or legal claims introduced by generated copy
- for material page work: Page Engine QA target >=85/100 with no hard failure in claim integrity, tracking/destination, mobile usability or product-media accuracy.

Maintain one canonical active production version per site. Keep rollback references. Do not delete historical deployments merely to make the dashboard look clean.

For ChatGPT-created or other builder sites use an adapter abstraction: read -> edit -> deploy -> verify. If a write adapter is unavailable, record pending_action rather than pretending the change was applied.

## Autonomy levels
AUTO:
- analytics instrumentation and repair
- metadata/schema fixes
- internal-link and broken-link fixes
- image/performance optimizations that preserve content meaning
- technical SEO and crawlability fixes

AUTO + MEASURE:
- CTA wording/placement
- page-section ordering
- trust signals
- affiliate-link prominence
- non-destructive conversion copy/layout changes grounded in existing evidence

EXPERIMENT:
- larger CRO/layout changes with explicit baseline/measurement and rollback.
- demand-led landing/content variants where the underlying market thesis is already validated.
- Page Engine angle/message-match/component-order variants with explicit parent page and hypothesis.

USER APPROVAL REQUIRED:
- domain ownership/changes
- pricing changes
- payment/checkout settings
- legal/compliance claims
- credential rotation/disclosure
- destructive deletion of production projects/data
- irreversible major redesigns

## SocialMarket AI Admin
Do not create a second admin dashboard. SocialMarket AI Admin is the single status/control interface for:
- Portfolio
- Analytics
- Greek Demand Intelligence
- Competition / Whitespace
- SEO
- CRO
- Experiments
- Deployments
- Data freshness/imports
- Agent activity
- Daily actions and results

Each public site should surface a compact joined status:
`Traffic | Conversion | Greek Demand | Competition/Whitespace | SEO | CRO | Deployment | Data Freshness | Recommended Next Action`.

SocialMarket AI is the controller, not an optimization target. SocialScheduler is publishing infrastructure, not an optimization target.

## Daily run
The daily orchestrator must:
1. Validate site registry and canonical production mappings.
2. Ingest/aggregate latest telemetry by site and page.
3. Validate conversion CSV freshness and coverage.
4. Create a data-upload email request only when required.
5. Map each eligible commercial page/site to canonical SocialMarket category/subcategory/product/pain intent with confidence.
6. Pull current Greek Demand Intelligence, Competition Gap, Demand Beacon/Solution Whitespace, pain-gap, seasonality and contradiction state without overwriting canonical truth.
7. Detect traffic, SEO, conversion, market-demand, affiliate-link, performance and runtime anomalies.
8. Rank opportunities by Growth Priority Score using both site-performance evidence and market-intelligence context.
9. Acquire site-level lock before assigning execution.
10. Run the minimum specialist agents needed for each high-value opportunity.
11. For any material page/campaign creation or rebuild, route through AFFINITY Creative Production/Page Engine and require selected angle, message match when applicable, archetype, Page DNA/component plan and measurable hypothesis before implementation.
12. Execute only safe/reversible actions that meet autonomy policy and evidence thresholds.
13. Deploy through the correct adapter and run quality gates.
14. Roll back regressions automatically when permitted.
15. Update SocialMarket AI Admin status, metrics, market context, action history and learning records.
16. Release locks and persist the daily portfolio summary.

## MyAgenticTeam integration
Use MyAgenticTeam as a coordination/execution adapter for delegated implementation work. The Growth Orchestrator remains the source of prioritization and governance; MyAgenticTeam may execute delegated specialist-agent work but must not create a parallel source of truth, independent schedules, conflicting site actions or a second demand model. Sync task status and outcomes back to Supabase and SocialMarket AI Admin.

When a task depends on market intelligence, hand MyAgenticTeam only canonical IDs, bounded evidence summaries, confidence, hypothesis and acceptance criteria—not raw full-page research dumps or invented metrics.

When a delegated task is material page construction, also hand MyAgenticTeam the approved AFFINITY context brief/angle/archetype/Page DNA/component plan or instruct it to generate them through the canonical Page Engine before code changes. MyAgenticTeam must not bypass the Page Engine with a free-form redesign.

If MyAgenticTeam execution is unavailable, continue the same canonical workflow through existing adapters. Never claim MyAgenticTeam work was executed without verification.

## Non-negotiable rules
- Supabase is the operational source of truth.
- SocialMarket AI canonical market intelligence remains the source of truth for demand/competition/pain/opportunity metrics.
- SocialMarket AI Admin is the only admin/status surface.
- One Growth Orchestrator controls all specialist agents.
- No duplicate independent daily automations for the same responsibility.
- No duplicate demand model inside GrowthOps.
- Evidence before optimization; measurement after every material change.
- Preserve working production and rollback capability.
- Material page/campaign creation must use the canonical AFFINITY Page Engine and Component Registry; do not generate free-form page structure when the governed workflow applies.
- PagePilot/Magnetic techniques are abstract production patterns only; never copy proprietary vendor code or exact protected designs.
- Never invent analytics, conversions, rankings, demand, competition, search volume, CPC, commissions, deployment success or experiment lift.
