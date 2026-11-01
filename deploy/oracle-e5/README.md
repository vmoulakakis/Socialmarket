# SocialMarket AI 3.0 — private ARM64 E5 inference runtime

**Purpose:** run the EXACT `intfloat/multilingual-e5-small` encoder used to populate
`sm_intel.search_documents.embedding` (384 dimensions) on the existing 2-OCPU,
12GB RAM Oracle ARM64 environment. This is a deployable package, not evidence of
a running Oracle service.

## Security architecture

- Model endpoint `/embed` requires server-only 32+ character bearer token and
  accepts only bounded JSON `{"query":"..." }`. Up to two concurrent requests.
- `/health` returns model/version only, not database, URLs, access tokens, content.
- Docker publishes **host loopback only** `127.0.0.1:8091`. It is NOT publicly
  accessible, and is NOT suitable as the Supabase Edge Function URL until a
  proper HTTPS authenticated reverse proxy or private gateway is installed.
- No database connection string is injected into the long-lived query service.
- Container runs nonroot, with dropped capabilities, read-only rootfs, CPU,
  memory and PID limits. First boot downloads the official Hugging Face model.
- Never print or commit the `SOCIALMARKET_EMBED_QUERY_TOKEN` secret.

## Operator checklist (not yet executed)

1. Independent review of Dockerfile, pinned dependencies, hashes, scan and
   private DNS/TLS design; enforce firewall block for inbound 8091.
2. On the Oracle ARM64 host install Docker/Compose if permitted; clone the reviewed
   repository **at an audited commit**, not an unreviewed branch.
3. Install a root-owned `/etc/socialmarket-e5/secure.env` with file mode 0600 and
   line `SOCIALMARKET_EMBED_QUERY_TOKEN=<32+ random chars>`. Do not share it in chat.
4. Run `docker compose -f deploy/oracle-e5/compose.yaml build` and
   `docker compose -f deploy/oracle-e5/compose.yaml up -d`.
5. Check `docker compose ps`, the **local** `http://127.0.0.1:8091/health`
   and actual signed request via `curl` with token loaded from a local secret store.
6. Route only via HTTPS with server-only authentication to existing
   `socialmarket-graphrag` Edge endpoint, then set server secrets
   `SOCIALMARKET_EMBED_QUERY_URL` and `SOCIALMARKET_EMBED_QUERY_TOKEN`.
   The Edge endpoint rejects non-HTTPS URLs.
7. The **production vector backfill is a separate one-time reviewed action**:
   use `.github/workflows/socialmarket-e5-protected-backfill.yml` after the
   approved revision has merged, the GitHub environment was configured and
   the correct VMDB scoped database credential was installed; start with 16 docs.
8. Compare Greek query results with hand-labeled holdout. If model accuracy or
   resource consumption is poor, stop without exposing product recommendations.

## Deployment status

Code staged only. **Not deployed to Oracle**; no credentials nor host agent
execution were available in this transaction. No network/model token spending.
