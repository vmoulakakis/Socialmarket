# AI Agency — 7 Repo Integration Decision

Reference video identified seven agent-engineering projects:
- rohitg00/agentmemory
- volcengine/OpenViking
- browser-use/browser-use
- ai-boost/awesome-harness-engineering
- mukul975/Anthropic-Cybersecurity-Skills
- cathrynlavery/diagram-design
- K-Dense-AI/scientific-agent-skills

## Decision
We adopt capabilities, not an uncontrolled dependency pile.

### AgentMemory
ADAPT.
Use its persistent-memory principles, but keep Supabase as canonical business memory to avoid a second operational data store.

### OpenViking
ADAPT, NOT DEFAULT RUNTIME.
Use hierarchical L0/L1/L2 context loading and inspectable context structure. Do not add an AGPL context database unless future scale proves Supabase retrieval insufficient.

### Browser Use
OPTIONAL FALLBACK.
Prefer existing connected browser/search/Work browser. Add Browser Use only for execution gaps that native tooling cannot cover.

### Awesome Harness Engineering
ADOPT PATTERNS.
Use explicit task graphs, evaluations, permissions, observability, failure classification and repair loops.

### Anthropic Cybersecurity Skills
SELECTIVE DEFENSIVE USE ONLY.
Do not import hundreds of dual-use skills into the growth agency. Use defensive controls relevant to secrets, prompts, dependencies, auth, tenancy and tool safety.

### Diagram Design
ADAPT.
Add diagram generation as a client communication capability. Prefer editable HTML+SVG and brand-aware outputs.

### Scientific Agent Skills
ADAPT RESEARCH DISCIPLINE.
Use hypothesis/evidence/contradiction/confidence patterns for market and business research. Do not import unrelated scientific domain packages.

## Outcome
The agency stack remains:
BYOK LLM Router + Supabase Memory/State + MyAgenticTeam + Connected Tools + Skills + Policy/Evals + Audit/Measurement.
