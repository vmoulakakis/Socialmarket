# Awin-only Application Autopilot — browser execution contract

**Publisher:** 3060863. **Evidence date:** 28 October 2026. **State:** Prepared queue / NO automated Join submitted by this repository.

This module is deliberately independent of production website changes. Data under `data/awin/application-queue.json` contains verified Awin membership snapshots, observed advertiser-level EPC metrics and tailored Greek application notes of at most 150 Unicode characters. These KPIs are not the publisher's earnings, and unknown commissions must remain unknown.

## Baseline
Joined 0; Pending: Back Market GR (30859), Water to Go Europe (107764). Not Joined: 12 programmes whose Greek primary region is GR. The Awin `status=Active` property indicates an advertiser programme is active, NOT that the publisher has Joined. Only actual membership / relationship qualifies.

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

### Current hard blocker
Chat-mode Awin MCP **has no join/apply tool**. Chat Browser plugin is read-only. The user has been offered TinyFish browser connector; the suggestion alone does **not** install it. Work mode also provides a cloud browser where available. Until an authenticated browser with action tools is connected, all five prioritized candidates are blocked at `publisher_site_unverified` and `advertiser_terms_unreviewed`; no application is submitted.

## After merchant approval
- Awin MCP `awin_create_links` can generate a tracked advertiser homepage or approved deep link **only after membership=Joined**. Never call it for non-Joined programmes or represent a standard clickThroughUrl displayed in the public programme directory as an approved tracking validation.
- Verify real CPA/CPS commission and realistic payout >=EUR 10 on relevant products (not a blanket assumption based on EPC).
- Verify actual Awin feed rights, accurate prices/stock/product data, merchant channel policy, affiliate disclosure and legal commercial hosting.
- Persist a verified link record and read-only audit log. If approval status reverses, stop publication.

## Verification
Run `node --test tests/awin-autopilot.test.mjs` and `node scripts/awin-autopilot.mjs`. GitHub CI checks that two Pending programmes are never re-applied, no joined claim is inferred from active programme status, no application passes without verified site + terms and no tracking can be considered eligible before Joined+commission+tracking verification.

## Evidence and research
- Awin publisher programme join message, promotional type and terms: https://success.awin.com/articles/en_US/Knowledge/How-do-I-join-an-advertiser-programme
- Awin program status API: https://help.awin.com/apidocs/get-program-information
- Awin Publisher API tools: https://help.awin.com/apidocs/for-publishers

Change ID: CHG-AWIN-20261028. Plan → GitHub branch and tests → review → connect supported browser operator → explicit licensed Join → API confirmation → approval watch → feed/link gates.
