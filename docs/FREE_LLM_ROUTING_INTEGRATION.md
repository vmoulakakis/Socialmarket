# SocialMarket — MyAgenticTeam free LLM integration (2026-11-09)

This application retains its ONE canonical lib/model-router.js and its remote_llm_calls / llm_output_tokens reservation/finalization ledger. The new free-first route is opt-in and does not alter affiliate selection, RAG evidence, seller approvals, or production deploy permissions.

## Setup
1. Create an API key in the official provider console. Do not paste keys into GitHub or browser.
2. Add GROQ_API_KEY and/or OPENROUTER_API_KEY as Vercel **server-only** environment secrets.
3. For Groq, check the provider account is actually on free tier, then set GROQ_FREE_TIER_CONFIRMED=true.
4. Enable FREE_LLM_FIRST_ENABLED=true and FREE_LLM_ONLY=true to prohibit paid model fallback. Set on preview first; verify live safe admin agent call and budgeting, then separately promote to production.
5. If FREE_LLM_FIRST_ENABLED remains false, the existing DeepSeek/OpenRouter/Supabase flow remains as before. If enabled, the sequence is Groq GPT-OSS 20B -> OpenRouter free-only -> (only if FREE_LLM_ONLY=false) old paid+Supabase routes.

Free-tier quotas are not unlimited. Groq free cap is account-dependent and includes token/rate constraints. OpenRouter free is usually 50 req/day and 20 RPM. Fallback only uses free model IDs (:free) or openrouter/free under free-only policy.

App API /api/agent is ADMIN AUTHENTICATED; it is not a public, unauthenticated LLM proxy. Every attempted provider call continues to be budgeted with existing Supabase remote_llm_calls and output tokens. Tool calling stays on existing policy.

Reference control plane: vmoulakakis/Myagenticteam (Free LLM Routing skill), commit 925e5487. Product's own router remains canonical. The public awesome-free-llm-apis catalogue provides discovery only, not keys.

Tests:
  node --test tests/free-llm-policy.test.mjs
  npm run test:orchestrator
