# Buyer Agent V2 — Release/Operator Gate

Change: CHG-SM-BUYER-20261106 · Branch: feat/agentic-shopper-evidence-gate-20261106
State: REVIEW / NOT PROMOTED TO PRODUCTION

## What actually exists

- Public \`/marketplace/advisor\`: read-only Greek buyer-intent matching of the old LuxeCorner 100-product collection. The source does NOT contain stock or independent evidence fields. Therefore products are labelled as research candidates; no audited recommendation is fabricated.
- Private \`/admin/buyer-agent\`: functional orchestration surface behind canonical Supabase admin authentication. Runs a deterministic source preflight. It can invoke two separate AI roles (Product Fit Research → Skeptic) through the **existing** \`lib/model-router.js\`, **only** when owner cost controls permit it. Strict JSON referents, two calls maximum at application layer, and skeptic/veto are checked. Even a model VALIDATED verdict cannot override missing source evidence.
- \`lib/linkwise-identity.mjs\`: reads a Linkwise CD104 route and compares it against authoritative program/merchant records. Parsing numeric ID NEVER becomes merchant approval. Only a canonical, current, approved program and merchant may pass. Tracking URL is never constructed or modified.
- \`docs/sql/SHOPPER_LINKWISE_PROGRAM_AUDIT.sql\`: safe read-only source diagnostic for VMDB. No migration or production data writes.
- CI validation: \`npm run test:shopper-agent\` plus \`npm run test:shopper-crew\` (mocked model outputs and safe holds).

## Observed source blockers (2026-11-06/07)

- 23,613 raw feed offers, 14,349 with program_id='unknown'.
- All 14,349 unknown-program rows contain a network route ID; six distinct program codes. The largest (program 399) has 12,807 \`in_stock=true\` rows, but this is *not* evidence of affiliate commission.
- None of the six route IDs has a matching confirmed row in \`linkwise_program_commissions\`. Therefore commission values of those 14,349 cannot safely be inferred from merchant names, price, domain or rates for unrelated programs.
- 8,921 La Redoute rows have 10% table-estimated commission but \`in_stock=NULL\`, often a source availability string such as "Διαθέσιμο από 7 έως 12 ημέρες". NULL is neither false nor current-confirmed true.
- Merchant profiles: 16 active, 0 program_approved, 0 tracking_verified. Do not relax the approval policy just to fill the product collection.
- Earlier September AI marketplace views are not current-canonical approvals.
- The ranking order and exact affiliate link must prioritize buyer need/offer truth, not commission amount.

## MyAgenticTeam role boundaries

1. **Source integrity**: strict canonical identity, source timestamp, stock, merchant approval, Linkwise URL structural route and conservative commission.
2. **Buyer intent**: need, price cap, buyer constraints; deterministic before any model.
3. **Product Fit Research Agent**: model can draft only source-grounded, non-authoritative hypotheses using 4 bounded products. No affiliate URLs, raw feed or credentials in model messages.
4. **Skeptic Agent**: independent review of all proposed referents, limitations and contradictions. A model cannot override missing independent evidence; the final state remains NEEDS_EVIDENCE or REJECTED.
5. **UX presentation**: explicit unknowns and verified/nonverified distinction; no misleading "AI selected verified best buy".
6. **Publisher**: none. SocialScheduler ownership is unchanged. No silent outbox or third-party posts.

## Live model policy (OFF by default)

The private admin route accepts \`run_model: true\` but will **not** call a provider unless BOTH:
- \`SHOPPER_BUYER_CREW_ENABLED=true\`
- \`ENABLE_PAID_REMOTE=1\`

are explicitly set on the trusted server by an authorized operator and provider credentials are configured. Actual cost authorization and daily/monthly quotas remain enforced by \`reserve_agent_budget\`. This is NOT an approval to enable spending. No public LLM inference or anonymous chat is introduced. If providers are unavailable, safe hold is returned; no fake "success" badge.

**Important:** the database budget policies presently permit some remote calls in general, but that is not specific owner authorization for this new buyer agent. Keep the new gate off until authorized.

## Immediate operational prerequisites for a genuine live agent

- Import current Linkwise joined-program metadata for the six IDs from the approved CD104 publisher account. Resolve one program ID to exactly one merchant/domain and current membership; do not infer program IDs from price or similarity.
- Refresh availability, currency, last_seen and commission rule provenance. Separate UNKNOWN / TRUE / FALSE stock; do not coerce NULL to false or true.
- Produce a bounded audited candidate set with actual evidence source IDs, skeptic outcomes and freshness, using the existing VMDB canonical data and respecting RLS. Do not grant public access to raw private feed tables.
- After verifying the canonical dataset, evaluate AI model quality against labeled Greek buyer needs and confirm provider charges. Public rate limiting/abuse controls are mandatory before public inference.
- Production deploy and ChatGPT Sites editing are separate release actions. Preview build does not update \`socialmarket-ai.vmoulakakis.chatgpt.site\`.

## QA and rollback

Review PR diff/CI/status. Test login, disabled model path, semantic input, empty result, mobile layouts, product details, affiliate URLs and error handling on Vercel Preview. The current CI runs no real external AI calls. Absence of browser screenshots means visual QA is UNVERIFIED.
Rollback is simply to leave the PR unmerged or revert it. Existing admin/merchant/publisher workflow is unchanged.
