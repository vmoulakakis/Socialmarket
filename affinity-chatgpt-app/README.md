# AFFINITY ChatGPT App

MCP app surface for the canonical `skills/AFFINITY_SKILL.md` framework.

## Archetype
Tool-only MCP app first. A widget can be added after the core research/API tools are connected.

## Tools
- `affinity_policy` — canonical Greece-first policy and gates.
- `evaluate_candidate` — deterministic hard-gate evaluation.
- `plan_research` — evidence-first research plan.

## Run
```bash
npm install
npm start
```
The MCP endpoint is `/mcp`.

## Production integration roadmap
1. Wire the existing server-side AliExpress affiliate gateway.
2. Add authenticated product discovery/commission verification.
3. Add Greek market research sources and evidence ledger.
4. Add Link Vault and tracking validation.
5. Deploy this MCP endpoint publicly over HTTPS.
6. Connect the MCP server to ChatGPT as the AFFINITY app/connector.
7. Complete app metadata/submission if public directory distribution is desired.

## Security
Never put AliExpress App Secret or other signing credentials in this package or browser code. Keep them in server-side secret storage.

## Canonical skill
The full operating specification remains `skills/AFFINITY_SKILL.md`; this app exposes executable tools based on that policy.
