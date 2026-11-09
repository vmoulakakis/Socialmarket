# Free LLM worker migration — GitHub Models retirement remediation

Date: 2026-11-09. GitHub officially retired GitHub Models on 2026-07-30, including the inference API. See https://github.blog/changelog/2026-07-30-github-models-is-now-retired/.

The old Python agentic pipeline, hourly GitHub code executor and Merchant Demand 360 judge contained calls to the retired models.github.ai domain. These are now replaced with two eligible and fixed routes:
- Groq official free-tier GPT-OSS 20B, when GROQ_API_KEY is configured and GROQ_FREE_TIER_CONFIRMED=true.
- OpenRouter openrouter/free, when OPENROUTER_API_KEY is configured.

No API key is generated or committed. Without eligible provider keys, remote free model judgment fails closed to deterministic/needs-review or to an existing retryable state. Neither GitHub token nor a paid DeepSeek/OpenAI key is silently used as fallback. Local Ollama and deterministic research remain separate.

## Privacy approval (mandatory)
These worker payloads may include proprietary merchant metrics or repository code. Free providers are **external processors**; do not share this information merely because a key exists. The following explicit GitHub Actions *variables* default to false:
- FREE_AGENT_EXTERNAL_ALLOWED: authorize sending evidence packets to remote free APIs from the scoped agentic pipeline, after data review.
- FREE_CODE_EXTERNAL_ALLOWED: authorize sending reviewed private repo snippets for bounded AI code tasks.
- FREE_MERCHANT_EXTERNAL_ALLOWED: authorize sending merchant scoring evidence/metrics to the external free judge.

After reviewing provider data retention, privacy policy, free commercial-use eligibility, rates, task size and data classification, set the appropriate opt-in variable. In particular, do not transmit credentials, private financial or personal records to free APIs. When these flags are false, existing local/deterministic mechanisms continue.

GitHub Actions repository secrets: GROQ_API_KEY and/or OPENROUTER_API_KEY. GitHub Actions variable: GROQ_FREE_TIER_CONFIRMED=true if officially verified. Vercel app environment secrets are independent and already covered by docs/FREE_LLM_ROUTING_INTEGRATION.md. No provider keys exist in currently audited Vercel environments.

No external API call has been made by these tests. The unit checks only validate fail-closed behavior, routing and Python compilation. Production semantic accuracy and provider availability remain UNVERIFIED until configured and replay-evaluated. Scheduled workflows and approval gates remain governed by the existing policy.
