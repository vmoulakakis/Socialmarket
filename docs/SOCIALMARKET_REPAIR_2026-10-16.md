# SocialMarket canonical VMDB repair

The production UI queried legacy relations and RPCs removed during the move to VMDB. The admin allowlist was also empty, so a valid password alone could not authorize database access.

## Changes

- Restore only the existing verified, pinned admin account to the allowlist.
- Add a bounded, admin-only workspace API in a private schema with an invoker public wrapper. No new direct table grants; unknown sections rejected.
- Read merchants, demand/problem clusters, feed offers, final selections, creative briefs, publishing jobs, pipeline runs and policies from canonical VMDB tables.
- Add offer search/pagination, detail inspection, error recovery and overdue publishing notices.
- Keep imported feed inventory separate from final AI product selection. Unknown scores remain null.
- Connect the public catalog/detail flow to the existing public LuxeCorner catalog rather than a nonexistent semantic marketplace view. The public catalog is labeled as the home collection, not as completed problem/solution AI curation.
- Stop silently using a legacy service-role credential against the VMDB URL.
- Add an admin-authenticated, budgeted DeepSeek Edge endpoint. The provider key is read inside the server from the existing Vault entry; no key is returned. Select a model only from the provider's live model list.
- Fix the auth callback lock hazard and stale sign-in timeout message.
- Guard cost-bearing AI routes and remove misleading deterministic creative fallback claims.

## Validation

Production build and existing design/demand/orchestrator contracts pass locally. SQL tests exercise every workspace section, disjoint pagination, empty search, invalid-section rejection, anon denial and non-admin denial. The new Edge deployment bundles successfully. Local Deno typechecking was blocked by registry network access; CI includes the check.

## Remaining operational constraints

At inspection: 16 merchants, 11 assessed/ranked, 0 final eligible merchants, 41 problem clusters, 5 demand assessments, 3,921 imported offers, 0 final selected products, 37 creative presentations and 37 jobs marked scheduled. These are stored statuses, not proof of current provider publication. Twenty-one semantic embeddings are pending and no first-party conversion events exist.

Some legacy discovery/research workflows deliberately remain manual-only because their gateways used the deleted project. The canonical Merchant Demand Intelligence 360 workflow uses VMDB and remains weekly. Do not reactivate deleted gateways, invent approval/tracking evidence, or lower selection gates to fill the UI.

A browser sign-in attempt was rejected by the site. Authenticated production UI/AI request verification therefore still requires a successful admin sign-in. No password was read or changed by the agent.

Rollback the application to commit ce46efa7ee6aa0019cfccc6186b2c939549446be if needed. The new read API is additive and does not change existing business records. Restoring the intended admin allowlist fixes the existing control-plane authorization.
