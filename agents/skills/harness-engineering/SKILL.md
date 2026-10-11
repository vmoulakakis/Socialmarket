# Agent Harness Engineering Skill

Version: 1.0
Purpose: Make agent execution reliable, observable, bounded and repairable.

## Principle
Model intelligence is not enough. Reliability comes from the harness: context, tools, state, permissions, evaluation, retries, monitoring and rollback.

## Execution graph
Mission -> Plan -> Steps -> Tool tasks -> Evidence -> Review -> Deliverable -> Measurement -> Learning.

Each step requires:
- step_id
- capability
- dependency list
- input schema
- output schema
- allowed tools
- max attempts
- timeout
- approval flag
- acceptance test
- rollback/recovery rule

## Replanning
Replan only when:
- new evidence invalidates an assumption
- a dependency fails
- cost/time ceiling changes
- acceptance test fails

Do not replan because the model merely has a different idea.

## Retry
Classify failures: transient, auth, validation, rate limit, tool mismatch, evidence gap, policy block.
Retries must change something meaningful: delay, tool, query, scope or input.

## Evaluation
Every material output must have a deterministic or rubric-based check.
Examples:
- technical SEO: canonical/robots/schema checks
- code: build/tests
- research: source coverage + contradiction check
- creative: brief/brand/message-match checklist
- outreach: target/claim/compliance checks

## Observability
Persist run, step, tool, cost, latency, result, error, approval and final status.
Never claim an action succeeded until verified.

## Cost-first routing
Use cheapest capable model/tool first.
Escalate when evaluation fails or task complexity justifies it.
Never expose provider keys to clients.
