# CHG-20261108-STREAMING-EUR15 — plan

1. Inspect actualrepo, deployedgateway, cron and DB counters. DONE.
2. Reuse PR103 fullfeed path; add single-pass transport, inventoryjournal, bounded all-eligible writes and strict completion. DONE.
3. Add begin/checkpoint/finalize to existing authenticatedgateway; no schema changes. DONE.
4. Add source researchledger and source-linked signals with explicit missingness. DONE.
5. Run offline failure/recovery/admission tests and independent review; syntax/typecheck gateway where runtimeavailable.
6. Save scoped changes on authorizedexistingfeaturebranch, deploy compatiblegateway, launch bounded-time fullworkflow through existingpush trigger. Check realrunstate and counters. Never call pending/partial a completed3.5m scan.
7. Record checks and runtime evidence in review.md / production-signal.md.
