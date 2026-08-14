# SocialMarket AI — Greek Opportunity & Publishing Intelligence

SocialMarket AI is the **single source of truth for merchant intelligence, opportunity ranking, approved content and publishing intent**. It discovers and evaluates opportunities; it does **not** call Buffer directly.

## Core architecture

1. immutable source import
2. merchant/program normalization
3. commercial affiliate scoring
4. evidence-backed trust / SEO / competition / Greece-market research
5. peer-group + global opportunity ranking
6. semantic merchant vectors (`BAAI/bge-m3`, 1024 dimensions)
7. brand/site selection
8. approved canonical content
9. per-platform jobs written to `publish.outbox`
10. SocialScheduler executes those approved jobs in Buffer
11. execution/reconciliation status is acknowledged back to SocialMarket

## Ownership boundary

### SocialMarket AI owns
- merchants and affiliate programs
- commercial metrics and score confidence
- trust / reputation evidence
- SEO and brand visibility evidence
- competition and Greece-market fit
- merchant taxonomy / peer groups
- rankings and semantic vectors
- brands & sites registry
- content strategy and approval
- canonical content items
- publishing outbox and final status

### SocialScheduler owns
- Buffer authentication
- Facebook / Instagram / TikTok routing
- exact scheduling of SocialMarket-selected times
- media readiness
- duplicate prevention
- rate-limit / retry safety
- Buffer reconciliation
- status acknowledgement

**SocialScheduler must not invent independent production campaigns or maintain a second production content backlog.**

## V2 data contract

The clean V2 Supabase project is `socialmarket` (`rpfadpdnnxequgvdcfoq`). Legacy SocialMarket migrations are not replayed into this database.

Internal schemas:
- `raw` — immutable imports
- `catalog` — canonical merchants/programs/taxonomy
- `intel` — commercial + research snapshots/evidence
- `ai` — semantic objects/vectors
- `ops` — research jobs + executor controls
- `content` — brand/site registry and approved content
- `publish` — publishing outbox
- `api` — read/query contracts

GitHub workers authenticate through GitHub Actions OIDC. No Supabase service-role key belongs in GitHub.

## Merchant research safety

- commercial metrics are not treated as consumer demand or trust
- research requires ≥3 evidence items from ≥2 independent domains
- empty search results never become a low merchant score
- AI narrative cannot overwrite deterministic scores
- vectors are created only after valid evidence-backed research
- classifier changes run as canaries before full-portfolio refresh

## Publishing safety

- every executable post requires an explicit `scheduled_for`
- SocialScheduler production claims remain database-disabled during import/dry-run validation
- dry-run uses non-mutating `peek`
- legacy backlog is import/rollback input only
- Buffer IDs/statuses are reconciled to prevent duplicate publication
- expired dates are never silently moved by the executor

See `supabase/v2/MIGRATION_MANIFEST.md` for the authoritative applied V2 migration and cutover contract.
