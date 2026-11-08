# CHG-20261108-STREAMING-EUR15 — intent

Owner request: full streaming ingestion, initial calculated affiliate commission >= EUR15, then evidence-driven pain/demand/competition/conversion ranking. Target existing SocialMarket + VMDB. No new orchestrator, public publishing or paid inference.

Source revision: main b282d8e74832ef7566f6667a6b1f247bc7cffbdb; reuse existing PR103 branch tip1f94906 because its fullfeed gateway is already deployed/authorized. Central governance revision1f119ef0ab3b2ada0b1883f5a93284c35b32be5c; plugin contract absent: SYNC_NEEDED.

Verified baseline: deployed legacy cron filters price>120, not commission, and can stop after an empty chunk. Main source differs from deployed source. Existing334 historical programme terms have only17 mappedIDs. Never infer3.5m scanned from a scheduler success.

Acceptance: stream without loading/downloading complete raw JSON; calculate from source terms; missing terms remainunknown; preserve tracking; persist ALL qualifying research rows in bounded batches; durable counts and inventory; nonzero exit on incomplete/undersized source or failed writes; no false demand/CVR claims. Commission qualification does not mean approved payable commission or promotion-ready stock.
