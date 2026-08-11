# SocialMarket TikTok Studio — Production Setup

## What is already implemented

- `/tiktok` admin UI: batch creator, AI copy refine, creative queue, approval and scheduling.
- Supabase tables for connections, batches, posts, attempts and metrics.
- TikTok OAuth Edge Function: `tiktok-oauth`.
- Background publisher Edge Function: `tiktok-publisher`.
- TikTok-safe photo preparation Edge Function: `tiktok-photo-prep`.
- `tiktok-media` public Storage bucket for TikTok PULL_FROM_URL media.
- Cron: publisher every minute, photo preparation every two minutes.
- TikTok media policy: no QR, no baked tracking URL, no promotional watermark/overlay.

## 1. Create / configure TikTok Developer App

In TikTok for Developers:

1. Add **Login Kit**.
2. Add **Content Posting API**.
3. Enable Direct Post when available for the app.
4. Request / configure scopes:
   - `user.info.basic`
   - `video.publish`
   - `video.upload`

### Redirect URI

Register this exact HTTPS redirect URI:

`https://prrehmcvpyhupvlhtbzg.supabase.co/functions/v1/tiktok-oauth/callback`

TikTok OAuth v2 uses `https://www.tiktok.com/v2/auth/authorize/` and the token exchange is server-side.

## 2. Configure Supabase Edge Function secrets

Set these as **Supabase Edge Function secrets**. Never commit the real values to GitHub.

- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_SCOPES=user.info.basic,video.publish,video.upload`

The OAuth health endpoint will report `configured: true` after the first two are set.

## 3. Verify the media URL prefix in TikTok

TikTok `PULL_FROM_URL` requires a developer-owned verified URL/domain prefix.

Current media prefix:

`https://prrehmcvpyhupvlhtbzg.supabase.co/storage/v1/object/public/tiktok-media/`

Prefer a custom SocialMarket media domain later and verify that instead, because it is easier to control and migrate.

## 4. Connect the TikTok account

Open the SocialMarket admin `/tiktok` page and click **Connect TikTok**.

The OAuth callback stores access/refresh tokens only in the Supabase `private` schema. They are never exposed to browser queries.

## 5. Audit / public posting

Unaudited TikTok Content Posting API clients are restricted to private (`SELF_ONLY`) posting. The SocialMarket publisher intentionally forces `SELF_ONLY` until the connection record is marked `audited=true` after TikTok approval.

After the TikTok app passes the required audit, set the relevant `tiktok_connections.audited` value to `true` from the private admin workflow.

## 6. Current launch batch

A `Launch Batch · Top 10` batch has already been created from the current SocialMarket top product opportunities.

The 10 items have TikTok-safe PHOTO media prepared in `tiktok-media` and are in `draft` state. They are **not scheduled or published** until a TikTok account is connected and the batch is explicitly approved/scheduled.

## 7. Scheduling flow

`Product opportunity → TikTok draft → TikTok-safe media → approval → scheduled_at → cron publisher → TikTok publish_id → status polling → published/failed`

The scheduler checks due posts every minute. It does nothing if there are no due posts.

## 8. TikTok media rules enforced by SocialMarket

- 9:16 target for generated creatives.
- No QR code in TikTok media.
- No baked affiliate/tracking URL in TikTok media.
- No promotional watermark or superimposed promotional branding.
- Caption/hashtags are stored separately from media.
- Direct Post queries fresh Creator Info before publishing.
- Media is served from a URL that must be verified in the TikTok Developer app.

## 9. Vercel

The GitHub code contains the `/tiktok` UI, but a Vercel project must be created/imported from `vmoulakakis/Socialmarket` before the admin UI is publicly reachable.

Public browser variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Optional server-side AI refinement:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_MODEL=deepseek-v4-flash`
- `OPENROUTER_API_KEY` (fallback)

TikTok client secret stays in Supabase Edge Function secrets, not in the browser.
