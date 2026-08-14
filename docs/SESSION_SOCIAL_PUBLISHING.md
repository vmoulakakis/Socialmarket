# Session-based social publishing

This document defines the no-developer-app publishing path for SocialMarket AI.

## Goals

- Keep the existing campaign, creative, approval and scheduling model.
- Add a second publishing route that uses authenticated user sessions instead of Meta/TikTok developer apps.
- Keep existing OAuth/API publishers as fallback until the session route is proven stable.
- Never commit cookies, passwords, tokens, storage-state files or service-role keys to GitHub.

## Provider strategy

| Platform | Default no-app route | Fallback | Notes |
|---|---|---|---|
| Instagram | session worker | existing Meta route | Use a persistent authenticated session; prefer private-session integration where available, otherwise browser automation. |
| TikTok | Playwright session worker | existing TikTok Direct Post route | Browser session uploads. |
| Facebook | Playwright session / Instagram cross-post | existing Meta route | Prefer cross-posting when the linked account supports it. |
| LinkedIn | assisted publish | manual browser | Keep the final publish action user-controlled by default. |

## Worker contract

A worker claims due jobs from `social_publish_jobs`, publishes through a provider adapter, records the result, and sends a heartbeat to `social_session_accounts`.

Required worker environment variables:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SOCIAL_SESSION_KEY` (used only by the local/session bootstrap process; never print it)
- `SOCIAL_WORKER_ID`

Provider sessions are kept outside the repository. The bootstrap command stores Playwright storage state in a local path or an encrypted secret store. `.gitignore` must exclude session files.

## Safety defaults

- Do not publish unapproved posts.
- Do not publish without media readiness for media-required platforms.
- Use idempotency keys per post/platform.
- Lock a job before publishing to avoid duplicates.
- Record every attempt and error.
- LinkedIn defaults to `assisted` mode rather than autonomous posting.
- Browser selectors are treated as versioned provider code and can fail closed when the platform UI changes.

## Rollout

1. Apply the session-publishing migration.
2. Pair one test account per platform.
3. Run the worker in dry-run mode.
4. Publish one private/test post per automated platform.
5. Enable scheduled claims only after the smoke test passes.
6. Keep API/OAuth publishers enabled as fallback during the transition.
