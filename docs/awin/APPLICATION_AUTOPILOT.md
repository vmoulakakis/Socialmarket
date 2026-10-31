# Awin-only Application Autopilot — browser execution contract

**Publisher:** 3060863. **Latest evidence date:** 31 October 2026. **State:** Prepared queue / NO automated Join submitted by this repository.

This module is deliberately independent of production website changes. Data under `data/awin/application-queue.json` contains verified Awin membership snapshots, observed advertiser-level EPC metrics and tailored Greek application notes of at most 150 Unicode characters. These KPIs are not the publisher's earnings, and unknown commissions must remain unknown.

## Baseline
Joined **0**; Pending: **Back Market GR (30859)**; Rejected: **Water to Go Europe (107764)**. Do not retry the rejected programme. The prepared queue contains 12 Not Joined candidates; only selected candidates were refreshed on 2026-10-30, and the queue is not a complete live programme census. The Awin `status=Active` property indicates an advertiser programme is active, NOT that the publisher has Joined. Only actual membership / relationship qualifies.

## Explicit application priority
1. Lambakaifotismos - GR (25829): task-based lighting / comparison, advertiser EPC €0.24 (historical aggregate). Commission unverified.
2. Hawkers GR (19725): sunglasses/use/UV guides, EPC €0.11. Commission unverified.
3. Elastika-Online GR (9837): dimension-based tyre purchase, EPC €0.11. Commission unverified.
4. Zooplus GR (24675): repeat pet care, EPC €0.06, historical advertiser description says up to 4% CPA; EUR 10 affiliate commission likely requires unusually large baskets, so **conditional**.
5. Autodoc GR (120141): vehicle maintenance / compatible parts, EPC absent; commission unverified. **Conditional**.

These are Awin-only pilots; they do not mean five currently ready-to-submit applications. Other available programmes remain in discovery for later fit/commission validation.

## Browser operator action contract (Work or connected authenticated cloud-browser agent)
- Navigate to **https://ui.awin.com/** via authenticated publisher browser profile, not via copied credentials in chat.
- Confirm the account **3060863** and actual approved promotional website/channel. The merchant must be able to access a **real, relevant, publisher-owned page**. Do not use an unrelated demonstration site, invent traffic metrics, or claim a product/service already launched if only in development.
- Review programme restrictions, allowed promotion methods, current commissions, exclusion categories, cookies/attribution and available feed; log terms evidence. Check the programme's actual status (never apply again to Pending/Joined/Rejected/Suspended without explicit review).
- Follow official Awin workflow: Advertisers / directory or individual advertiser programme → **Join** → choose truthful promotional type → paste the corresponding tailored message (max 150 characters) → review programme terms → apply with the user's authorization for this workflow; stop for unexpected legal/financial/irreversible terms.
- Immediately confirm the provider response and capture the actual outcome **Joined / Pending / Rejected / Error**, programme ID, timestamp and provider evidence. Do not label "submitted" from a click without confirmation.
- Recheck with Awin MCP `awin_get_programme_details` and the relationship list. Be mindful of propagation delays; do not blindly resubmit if an API still shows Not Joined shortly after a successful UI confirmation. Do not publish an affiliate link unless Joined and all merchant/commission/creative checks pass.
- Update queue status and source evidence via reviewed PR or approved persistence backend. Keep preflight evidence and images private; NEVER store Awin tokens or passwords in GitHub.
- Respect rate limits and avoid batch applications to poorly matched brands. Use one application per programme with idempotent provider status checks.

### Current hard blocker (30 October 2026)
Awin MCP **has no join/apply tool**. The Browser connector could not access Chrome tabs from this scheduled runtime because it requires the originating browser context. TinyFish is connected but the user explicitly disallowed its metered browser automation; do not invoke it. No alternate authenticated browser-write access was established. Until the authorized no-extra-cost browser is accessible, candidate applications remain blocked at `publisher_site_unverified` and `advertiser_terms_unreviewed`; **no new application was submitted**. This blocker has already been reported to the user; do not notify again unless the access situation materially changes.

## After merchant approval
- Awin MCP `awin_create_links` can generate a tracked advertiser homepage or approved deep link **only after membership=Joined**. Never call it for non-Joined programmes or represent a standard clickThroughUrl displayed in the public programme directory as an approved tracking validation.
- Verify real CPA/CPS commission and realistic payout >=EUR 10 on relevant products (not a blanket assumption based on EPC).
- Verify actual Awin feed rights, accurate prices/stock/product data, merchant channel policy, affiliate disclosure and legal commercial hosting.
- Persist a verified link record and read-only audit log. If approval status reverses, stop publication.

## Verification
Run `node --test tests/awin-autopilot.test.mjs` and `node scripts/awin-autopilot.mjs`. GitHub CI checks that Pending and Rejected programmes are not re-applied, no joined claim is inferred from active programme status, no application passes without verified site + terms and no tracking can be considered eligible before Joined+commission+tracking verification. Re-check the latest CI after each queue change; do not claim a local test run if not executed.

## Evidence and research
- Awin publisher programme join message, promotional type and terms: https://success.awin.com/articles/en_US/Knowledge/How-do-I-join-an-advertiser-programme
- Awin program status API: https://help.awin.com/apidocs/get-program-information
- Awin Publisher API tools: https://help.awin.com/apidocs/for-publishers

Change ID: CHG-AWIN-20261028. Plan → GitHub branch and tests → review → connect supported browser operator → explicit licensed Join → API confirmation → approval watch → feed/link gates.

## 2026-10-30 operational review

- Awin account verified: publisher **3060863**. Joined 0, Pending 1 (30859), Rejected 1 (107764), Suspended 0.
- Awin publisher advertiser performance query for **2026-10-01 through 2026-10-30**, UTC, returned an empty list. This is **no report rows**, not a verified zero payout or a basis for EPC inference. `Europe/Athens` was rejected by the API, so the query was retried successfully with `UTC`.
- Rechecked **Lambakaifotismos GR (25829)**, **Elastika-Online GR (9837)** and **Hawkers GR (19725)**: all **Not joined**. Merchant reported EPCs EUR 0.24, EUR 0.11 and EUR 0.11 respectively; these are advertiser-level KPIs, not publisher returns. All three `commissionRange` fields were empty; **actual payable commission and promotion terms are not verified**. Lambakaifotismos reported 50% conversion but no sample size; do not project from it.
- Limit editorial work to two exploratory themes: **refurbished electronics** (Back Market Pending) and **tyre compatibility** (Elastika Not joined). Two existing Buffer HOLD ideas already cover them. No new drafts, tracked links, public posts, deployments or paid browser sessions this run. Do not repurpose unrelated personal Instagram/TikTok channels without eligibility verification; `Sales for All` Facebook is disconnected and `my deal` startPage is locked.
- One experiment per funnel once approval and instrumentation exist. Primary KPI: **validated commission per qualified outbound click**; diagnose tracking and reversals before changing creative. Until then no statistically meaningful funnel experiment exists.
- Persistence: `data/awin/application-queue.json` contains the latest membership and operational status. This is review-only PR data; not merged to production.


## 2026-10-31 operational review

- Reconfirmed via Awin MCP account 3060863: **Joined 0**, **Pending Back Market GR (30859)**, **Rejected Water to Go Europe (107764)**, **Suspended 0**. Advertiser programme `status=Active` is not publisher membership.
- Rechecked three Greece-region candidates via `awin_get_programme_details`: **Lambakaifotismos - GR (25829)**, **Elastika-Online GR (9837)**, **Hawkers GR (19725)**. All remain **Not joined**. Their current advertiser-level EPCs are EUR **0.24**, **0.11**, **0.11** respectively; commissionRange is empty for all three. Do not estimate publisher earnings, demand, margin or commission from these figures.
- Awin advertiser performance for **2026-10-01 through 2026-10-30**, queried successfully using **UTC**, returned **0 rows**; pending/approved/reversed commissions remain **unknown**, not zero. `Europe/Athens` was rejected by the API; no more retries needed.
- Buffer channel check: **Sales for All** Facebook disconnected, **my deal** startPage locked; TikTok `billmtiktoker_ai` and Instagram `vassilis1969` connected but **affiliate relevance/merchant permissions not verified**. Existing two HOLD ideas were verified by ID; no publication.
- Authenticated Chrome connector in this scheduled runtime returned `originating_browser_context_required`. This is the **same previously reported browser blocker**, not a new incident. No paid TinyFish call, Join attempt, affiliate link, public post, deployment or paid advertising.
- Added `data/awin/operations-ledger.json` as **review-branch-only evidence**, with unique daily run key and two unique internal editorial campaign keys. These keys are **not Awin clickrefs**. A regression test now enforces duplicate-free run/campaign keys, no paid actions, no unapproved tracking/posts and null commissions when the report is empty. No public runtime/persistence is claimed.
- Limited exploratory themes to **refurbished electronics** (merchant Pending) and **tyre compatibility** (merchant Not joined). Lighting and sunglasses remain candidates, not active funnels. Seasonality and competitive hypotheses are **unverified**; there is no measured Greek keyword demand or price-comparison study yet.
- Next decision gate: browser operator with authenticated publisher site + advertiser terms review. Do not resubmit existing Pending/Rejected programmes. Only after verified Joined and product-level eligibility may tracking, live pages and organic affiliate posting proceed.
