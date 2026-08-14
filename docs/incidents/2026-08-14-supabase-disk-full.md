# Incident: Supabase PostgreSQL disk full

**Date:** 2026-08-14  
**Project:** `socialmarket-ai`  
**Project ref:** `prrehmcvpyhupvlhtbzg`  
**Severity:** Critical  
**Status:** Open / external infrastructure blocker

## Observed failure

PostgreSQL repeatedly reaches the end of crash recovery and then exits because it cannot create a temporary WAL file:

- `could not write to file pg_wal/xlogtemp...: No space left on device`
- subsequent `database system is not accepting connections`
- repeated automatic recovery / restart loop

The Supabase management status may still report `ACTIVE_HEALTHY`; PostgreSQL logs are the source of truth for this incident.

## Impact

- SQL migrations cannot be applied safely.
- Admin reads/writes may fail until PostgreSQL accepts normal connections.
- Product-to-Post scheduled workflow must remain unmerged/disabled on production because its required tables are not installed yet.
- Supabase Edge Functions can still be deployed independently; `buffer-sync` v2 was deployed with JWT verification enabled.

## Safe actions already taken

- Product-to-Post implementation remains in PR #4, not merged into `main`.
- Migrations are committed but intentionally not executed.
- Autonomous monthly-plan creation has a six-hour retry cooldown.
- Publishing is fail-closed with incident recording and bounded retries.

## Required recovery

Restore usable PostgreSQL disk capacity before applying migrations. On the current Free organization, paid-plan disk auto-scaling is not available. Once PostgreSQL accepts connections:

1. run a lightweight SQL health query;
2. inspect database/WAL size and largest relations;
3. recover/delete only verified disposable data if needed;
4. apply Product-to-Post migrations in order;
5. run Supabase security/performance advisors;
6. run one canary product campaign before merging PR #4.
