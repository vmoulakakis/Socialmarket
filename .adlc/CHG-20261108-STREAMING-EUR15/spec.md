# CHG-20261108-STREAMING-EUR15 — specification

Existing fullfeed entrypoint -> strict HTTP/local JSON array parser -> reused product/route validation -> source programme terms or unique exact source-site domain match -> unrounded >=EUR15 gate -> SQLite inventory/write-ahead inputcursor -> OIDC20-row/135KB upserts -> checkpoints -> evidence-aware ranked shortlist. Every qualifying row persists; top limits only report size. No stock, arbitraryprice, merchantquality or category hard gate. NonEUR/invalididentity and unavailablecommission are not calculable, not fabricatedlowdemand.

Source default is published known category IDs1..153, not publisher-certified universal coverage. expected_records3500000 is a user-supplied coverage threshold, not proof of complete network scope. Require valid EOF and observed count >=threshold to complete configuredinput; still scope_verified_by_publisher=false. Short/HTML/truncated/error inputs remainpartial. Directfeed with no strong ETag cannot safely resume an old ordinal: restart fresh. Local immutable source resume verifies path/stat, terms hash, signals hash and threshold. Replay to committed ordinal, never byte-range JSON offsets.

Unknown numeric demand/competition remainNULL. Research ledger includes contradictory Greek supply on major sites and no fabricated volumes. Outputs are private research candidates, not approval/publication. Original links preserved. Auth remains exactexisting GitHubOIDC branches/workflow.

Rollback: previous gateway source remains in git history; stop workflow; keep partial run and checkpoint artifacts; do not delete preexisting offers. Retire only obsolete price-only cron after replacement validation.
