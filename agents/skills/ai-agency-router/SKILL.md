# AI Agency Router Skill

Version: 1.0
Purpose: Convert a business outcome into the smallest qualified agent team, tool set, memory scope, approval plan and measurable execution graph.

## Core rule
Never start from a fixed list of agents. Start from the user's business outcome, evidence, constraints, available tools and risk.

## Routing sequence
1. Parse the mission: business, target outcome, deadline, budget, market, geography.
2. Retrieve persistent business memory and recent decisions.
3. Identify missing evidence only.
4. Diagnose the constraint: demand, visibility, conversion, offer, creative, sales, operations, data, technical delivery or mixed.
5. Activate the minimum specialist set.
6. Attach only tools each specialist requires.
7. Define deliverables, KPIs, approval gates and stop conditions.
8. Execute through the existing orchestrator/task graph.
9. Verify outputs and persist reusable learnings.

## Specialist capabilities
- Requirements / Diagnosis
- Research / Evidence
- Strategy
- SEO / GEO
- CRO
- Creative / Visual
- Web / Engineering
- Sales / CRM
- Analytics
- Automation
- QA / Security
- Deployment

## Example routing
More qualified leads:
Requirements -> Research -> ICP -> Offer -> Landing/CRO -> Outreach/Ads -> Analytics -> QA.

More search visibility:
Requirements -> Research -> SEO Black Belt -> GEO/AI Search -> Content -> Technical SEO -> Analytics -> QA.

Automate repetitive operations:
Requirements -> Process Mapping -> Tool Audit -> Automation -> Security -> QA -> Monitoring.

## Agent activation contract
Every activated agent must declare:
- mission
- bounded inputs
- allowed tools
- memory scope
- expected output schema
- acceptance criteria
- autonomy level
- cost ceiling
- timeout / retry policy

## Autonomy
AUTO: reversible read-only analysis, metadata fixes, safe diagnostics.
AUTO+MEASURE: reversible low-risk optimizations with explicit baseline.
APPROVAL: external publishing, outreach, material site changes, ads/campaign launches.
HUMAN ONLY: payments, credential disclosure/rotation, legal commitments, destructive actions.

## Memory
Use the persistent-business-memory skill. Do not dump full chat history into prompts.

## Browser
Use the browser-research-operator skill. Prefer already-connected browser/search capabilities before adding a second automation runtime.

## Security
All write actions pass defensive-agent-security policy and tool allowlists.

## Evidence
Do not invent rankings, traffic, conversions, costs, demand, competitor facts or execution success.

## MyAgenticTeam
MyAgenticTeam is the execution adapter. This Router owns decomposition and capability selection; the existing Growth Orchestrator remains authoritative for portfolio-wide prioritization where it is already governing a site.
