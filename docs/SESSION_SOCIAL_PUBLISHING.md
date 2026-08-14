# Session-based social publishing

This document defines the no-developer-app publishing path for SocialMarket AI.

## Goals

- Keep the existing campaign, creative, approval and scheduling model.
- Add a second route that uses an authenticated browser session without requiring a Facebook/Instagram/TikTok/LinkedIn developer app.
- Keep the existing OAuth/API publishers for true unattended publishing where configured.
- Never commit cookies, passwords, tokens, storage-state files or service-role keys to GitHub.

## Important boundary

The no-app route is intentionally **assisted**, not unattended. The worker verifies the saved session and prepares the exact caption/media/composer target, but the user performs the final Publish/Post/Share action. This keeps the route resilient and avoids pretending that unsupported browser automation is equivalent to an official publishing API.

## Provider strategy

| Platform | No-app route | Unattended fallback | Notes |
|---|---|---|---|
| Instagram | verified session + assisted composer | existing Meta route | Pair once, prepare media/caption, finish Share yourself. |
| TikTok | verified session + assisted upload composer | existing TikTok Direct Post route | Pair once, open TikTok Studio with the prepared package. |
| Facebook | verified session + assisted composer | existing Meta route | Prefer Instagram→Facebook cross-post when already configured. |
| LinkedIn | verified session + assisted composer | none by default | Final publish stays user-controlled. |

## Data model

- `social_session_accounts`: paired account metadata and worker health.
- `social_session_vault`: encrypted Playwright storage state; no normal authenticated read policy.
- `social_publish_jobs`: idempotent queue/history for the assisted route.
- `claim_social_publish_jobs(...)`: atomic `SKIP LOCKED` worker claim RPC.
- `social_session_worker_heartbeat(...)`: account/session health heartbeat.

## One-time pairing

Run pairing from a trusted local machine:

```bash
pip install -r workers/social_publisher/requirements.txt
python -m playwright install chromium
python -m workers.social_publisher.bootstrap_session instagram --label "SocialMarket Instagram"
```

Required local environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SOCIAL_SESSION_KEY`

The helper opens the real platform login page. You enter credentials and complete MFA directly in that browser. The script stores only encrypted browser session state in Supabase.

## Worker

The GitHub Action `.github/workflows/session-social-publisher.yml` runs every 30 minutes and can also be started manually. It claims due assisted jobs, verifies the paired session, downloads the prepared media when needed, and writes a ready-to-finish package back to the queue.

Required GitHub Actions secrets:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SOCIAL_SESSION_KEY`

## Dashboard

Open `/session-publishing` in the Next.js admin to:

- see paired account/session health,
- queue approved campaign posts,
- create a LinkedIn assisted draft,
- inspect ready/history jobs,
- copy the prepared caption,
- open the relevant platform composer.

## Safety defaults

- Queue only approved campaign posts.
- Use idempotency keys to prevent accidental duplicates.
- Keep encrypted session material inaccessible to normal client reads.
- Fail closed when a session expires or a platform login challenge appears.
- Use existing official OAuth/API publishers when unattended publishing is required.

## Rollout

1. Apply `20260814110000_session_social_publishing.sql`.
2. Pair one test account per platform from a trusted local machine.
3. Configure the three GitHub Actions secrets.
4. Queue one approved test post.
5. Confirm the worker changes the job to `assisted` and the dashboard shows Copy caption/Open composer.
6. Keep the existing Meta/TikTok/Buffer integrations enabled as fallback.
