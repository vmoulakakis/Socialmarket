# Conversation Handoff — SocialMarket GrowthOps

This file preserves the final decisions from the GrowthOps planning conversation so future work can continue without reconstructing the architecture from chat history.

## Final decisions
1. `GROWTH_ORCHESTRATOR` is the single master AI coordinator for the public-site portfolio.
2. Supabase stores analytics, state, experiments, locks, learning and runtime policy.
3. SocialMarket AI Admin is the only routine control/status UI; no second admin dashboard.
4. SocialMarket Greek Demand/Competition/Pain intelligence is canonical and is consulted before SEO/CRO/content decisions.
5. Existing SocialMarket market metrics remain authoritative and must not be overwritten by GrowthOps scoring.
6. Web analytics by site/page plus normalized conversion CSV are primary performance inputs.
7. If conversion data becomes stale, GrowthOps may continue with reduced confidence; user contact occurs only if missing data truly blocks required work and cannot be obtained elsewhere.
8. All new/revised pages, posts and creative marketing assets use AFFINITY plus the premium creative-production skill and the best-fit modern web-design framework for the project.
9. MyAgenticTeam is implementation/review/test support, not a second planner, scheduler or source of truth.
10. Safe/reversible fixes are autonomous. The user should not be asked to perform technical steps that available connectors can perform.
11. User contact is exception-only: new cost or a genuine capability/authentication/file/human-action blocker.
12. No routine completion email and no intermediate email. Routine reports stay in SocialMarket AI Admin/Supabase.
13. Duplicate automation is prohibited. Before adding a task, cron or workflow, compare responsibilities and called functions against existing automation.
14. SocialMarket AI and SocialScheduler remain infrastructure and are excluded from public-site optimization targets.

## Automation state captured from this conversation
- Daily GrowthOps: enabled and canonical.
- Daily Public SEO: disabled.
- Conversion Optimization: disabled.
- Affiliate Campaign Review: disabled and merged into Monday GrowthOps.
- Duplicate SocialScheduler auto-heal cron: disabled where AI autopilot already performs it.
- Duplicate SocialScheduler feedback sync cron: disabled where AI autopilot already performs it.
- Conversion cron: data/metrics preparation only, not a second CRO decision engine.
- Weekly SocialScheduler optimizer: one automatic canonical path; duplicate GitHub scheduled path changed to manual-only.

## Canonical repository references
### SocialMarket
`vmoulakakis/Socialmarket`
- `agents/skills/growth-orchestrator/SKILL.md`
- `docs/GROWTHOPS_FINAL_REFERENCE.md`
- `skills/AFFINITY_SKILL.md`
- `agents/skills/affinity-creative-production/SKILL.md`
- `agents/skills/demand-intelligence-v3/SKILL.md`
- `agents/skills/greece-market-intelligence/SKILL.md`
- `agents/skills/competition-gap/SKILL.md`

### MyAgenticTeam
`vmoulakakis/Myagenticteam`
- `GROWTHOPS_INTEGRATION.md`

## Canonical daily execution
1. Validate site registry and canonical production mapping.
2. Aggregate latest analytics by site/page.
3. Validate conversion-data freshness.
4. Map commercial intent to canonical Greek demand/competition/pain context.
5. Diagnose SEO, CRO, affiliate-link, performance and runtime opportunities.
6. Rank only evidence-backed actions.
7. Acquire site lock.
8. Delegate the smallest capable MyAgenticTeam pattern.
9. Apply safe/reversible changes directly.
10. Build/preview/deploy through the correct adapter.
11. Verify production and analytics.
12. Roll back regressions where permitted.
13. Persist results, experiments and learning to Supabase/SocialMarket AI Admin.
14. Contact the user only for a cost decision or a blocker that cannot be handled autonomously.

## Current philosophy
This is one controlled GrowthOps operating system with specialist workers under a single decision authority, not a collection of independent agents.
