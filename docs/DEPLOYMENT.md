# SocialMarket deployment

Vercel project: `socialmarket-ai-admin`

Production/admin routes to verify after deploy:

- `/product-to-post` — autonomous Product-to-Post control and CSV intake
- `/monitor` — publishing health, incidents, queue and click monitoring
- `/links/tiktok` — TikTok link-in-bio landing page
- `/go/[slug]` — tracked affiliate redirect

The application is connected to the Supabase project `socialmarket-ai`. Product-to-Post database migrations must only be applied when PostgreSQL is accepting normal connections.

A commit to `feat/product-to-post-engine` should create a Vercel Preview Deployment through the connected Git repository. Merge to `main` only after preview verification and database recovery.
