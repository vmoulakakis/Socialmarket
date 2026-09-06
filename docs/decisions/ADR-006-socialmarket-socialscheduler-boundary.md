# ADR-006 — SocialMarket / SocialScheduler Ownership Boundary v2

Status: **Accepted**  
Effective: **2026-09-06**  
Supersedes: ADR-006 v1 wording in this file

## Decision

Both applications use the same Supabase project:

`rpfadpdnnxequgvdcfoq`

There is one canonical data model. Neither repository may create a duplicate merchant, product, content, campaign or publishing truth store.

The boundary is semantic as well as technical:

- **SocialMarket decides what is commercially valid and what should be said.**
- **SocialScheduler decides whether and how an already-approved intent can be executed safely through a provider.**
- Provider success is never inferred from workflow success or elapsed time; it requires provider evidence.

---

## SocialMarket AI owns — canonical business intent

SocialMarket is the sole canonical owner of:

- merchant intelligence
- category/subcategory intelligence
- product intelligence and product eligibility
- commission/economic gates
- evidence, audit and falsification
- pain-gap discovery
- semantic vectors and opportunity ranking
- portfolio membership and portfolio type
- brand/site registry
- campaign strategy
- audience/angle selection
- canonical platform-specific copy
- hooks, body copy, CTA, disclosure and claims
- canonical hashtag/keyword intent
- affiliate/tracking URL
- creative concept and approved source creative
- approval state
- publishing priority
- intended publishing time or explicitly approved execution window
- canonical `content.items`
- canonical `publish.outbox`
- interpretation of post-publication performance

SocialMarket ends at **Approved Publishing Intent**.

### Product ownership rule

A product may enter or leave an executable portfolio only because SocialMarket's commercial/evidence layer changed its eligibility or rank.

SocialScheduler must not:

- discover a new commercial product and promote it directly;
- raise or lower product eligibility;
- substitute a different product because a provider lane is unavailable;
- reinterpret commission, scarcity, demand, pain or merchant evidence.

Any Scheduler role named `Product Scout`, `Opportunity Strategist` or similar is execution-side advisory only. It may prioritize **among already-approved intents** for capacity/fatigue reasons; it cannot create canonical commercial eligibility.

### Copy ownership rule

Canonical copy is SocialMarket-owned.

SocialScheduler may perform only deterministic execution-safe transformations that do not change meaning, including:

- provider-required line-break normalization;
- deterministic disclosure placement when the exact disclosure text is already approved;
- omission of unsupported provider-only formatting tokens;
- length validation and rejection;
- use of an explicitly pre-approved alternate variant carried in the publishing intent.

SocialScheduler must not independently rewrite:

- claims;
- price/discount statements;
- hook meaning;
- CTA meaning;
- affiliate destination;
- audience positioning;
- urgency/scarcity language.

If approved copy cannot satisfy a provider contract without a material rewrite, the intent returns to SocialMarket.

### Creative ownership rule

SocialMarket owns the commercial/semantic creative.

SocialScheduler may render or package an already-approved creative deterministically for provider requirements, including QR generation from the exact approved tracking URL, resizing and format conversion, provided no claim, product, CTA or destination changes.

---

## SocialScheduler owns — execution control plane

SocialScheduler is the sole canonical owner of:

- claiming approved jobs from `publish.outbox`;
- provider/account connectivity;
- provider health and readiness;
- provider selection among allowed executable lanes;
- technical preflight;
- media/provider contract validation;
- capacity and rate-limit handling;
- idempotency and duplicate prevention;
- transient technical retries;
- provider reconciliation/readback;
- external provider post IDs;
- external platform post IDs/permalinks;
- terminal publication/failure ACK;
- raw execution and provider telemetry.

SocialScheduler begins at **Execute Approved Publishing Intent**.

---

## Schedule ownership rule

The default contract is **immutable exact time**:

- `publish.outbox.scheduled_for` is the canonical target chosen by SocialMarket.
- SocialScheduler may not move it merely to fill a queue, balance providers or increase frequency.

An exception is allowed only when SocialMarket explicitly supplies an execution envelope in the approved intent, for example:

```json
{
  "scheduled_for": "preferred timestamp",
  "execution_window": {
    "earliest_at": "timestamp",
    "latest_at": "timestamp"
  }
}
```

When an explicit window exists, SocialScheduler may select the exact provider slot **inside that window** using capacity, fatigue and provider-health evidence. It may never move outside the approved window.

If no `execution_window` exists, `scheduled_for` is immutable.

This rule makes schedule optimization an execution concern only when SocialMarket has explicitly delegated a bounded window.

---

## Provider readiness and quarantine rule

A provider can be technically connected yet not assignment-ready.

Automatic assignment requires:

1. provider registry enabled;
2. connected/healthy provider account;
3. supported platform/account;
4. provider contract satisfied;
5. recent provider-confirmed publication evidence where the routing policy requires it.

A quarantined provider may remain connected for readback and diagnostics but receives no new automatic publishing intents.

Release from quarantine requires explicit provider-confirmed evidence recorded in the canonical delivery ledger. Workflow success, scheduled ACK, elapsed due time or a non-terminal provider state is insufficient.

---

## Publication truth rule

Canonical lifecycle states must distinguish at minimum:

- approved
- leased/claimed
- scheduled/provider-acknowledged
- published
- failed
- cancelled
- unknown provider state

A scheduled item whose due time passes without terminal provider evidence must not remain indefinitely represented as healthy scheduled capacity. It becomes an explicit unknown/reconciliation state until provider readback proves `published` or `failed`.

`published` requires provider evidence and, where available, provider publication timestamp plus external ID/permalink.

---

## Forbidden duplication

### SocialMarket must not contain

- provider execution logic;
- Meta/TikTok/LinkedIn account connection UI for publishing;
- provider credentials;
- independent provider scheduler queues;
- provider retry loops;
- provider-specific reconciliation logic.

### SocialScheduler must not contain canonical

- merchant/product intelligence;
- pain-gap ranking;
- campaign strategy generation;
- product eligibility/ranking;
- canonical copy generation;
- affiliate-link rewriting;
- commercial creative replacement decisions;
- independent business schedule generation;
- duplicate content/product tables.

Legacy Scheduler utilities that create campaigns, copy or product choices are non-canonical and should be deprecated or moved upstream to SocialMarket.

---

## Operational adaptation rule

SocialScheduler may retry the **same approved intent** after a transient technical failure when idempotency is preserved.

It may not invent a new:

- product;
- claim;
- caption meaning;
- affiliate URL;
- creative meaning;
- campaign;
- marketing time outside an explicitly approved execution window.

Business-level changes return to SocialMarket.

---

## Analytics rule

`Scheduler collects; SocialMarket interprets.`

Raw provider/execution/performance data can be collected by SocialScheduler and written to the shared database. Commercial learning, future product ranking, campaign decisions and canonical copy/creative strategy belong to SocialMarket.

Scheduler may learn provider reliability, provider capacity and provider execution timing inside explicitly delegated windows; it may not convert those observations into independent commercial strategy.

---

## Database rule

The shared database is the integration boundary. Cross-repository synchronization by copying canonical records is prohibited.

Views/RPCs may expose controlled projections, but physical source-of-truth records remain singular.

---

## Enforcement checklist

A change crosses the boundary incorrectly if any answer below is `yes`:

1. Can Scheduler create a product/campaign that SocialMarket never approved?
2. Can Scheduler materially rewrite copy or claims?
3. Can Scheduler change the affiliate destination?
4. Can Scheduler move an exact schedule without an approved execution window?
5. Can SocialMarket call a provider API directly to publish?
6. Can either repository maintain a second canonical content/product/publishing table?
7. Can a post become `published` without provider-confirmed evidence?

If yes, the change must be redesigned before production.
