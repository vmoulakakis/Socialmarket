# AFFINITY Page Engine — Prompt & Agent Contracts

Version: 1.0
Status: Canonical
Depends on:
- `skills/AFFINITY_SKILL.md`
- `skills/AFFINITY_PAGE_ENGINE.md`
- `config/affinity-page-engine.json`
- `agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md`
- `agents/skills/affinity-creative-production/PAGE_DNA.schema.json`

Purpose: eliminate vague one-shot page prompting. Each generation stage has explicit inputs, outputs, truth rules and stop conditions.

---

## Global contract

Every stage must:
1. consume only provided/canonical evidence plus clearly labeled inference;
2. preserve claim/evidence classes;
3. output structured data first when the downstream stage is machine-driven;
4. never fabricate missing commercial facts;
5. return `HOLD` with exact missing inputs when a hard dependency is unresolved;
6. avoid vendor-copy mimicry and proprietary source-code reproduction;
7. minimize duplicated prose between stages;
8. carry stable IDs forward so experiments remain attributable.

Recommended stage envelope:

```json
{
  "stage": "angle_matrix",
  "status": "PASS | HOLD | REJECT",
  "input_refs": [],
  "output": {},
  "assumptions": [],
  "unknowns": [],
  "warnings": []
}
```

---

# 1. SOURCE INGEST AGENT

## Goal
Turn URLs/files/campaign inputs into normalized factual source objects, not sales copy.

## Inputs
- product/merchant/supplier/competitor URLs
- user files/documents
- campaign/ad/email/social source
- existing site/brand context
- AFFINITY evidence ledger.

## Must extract
- source ID and type
- canonical product/model/offer identity
- factual specifications
- price/offer snapshot with timestamp
- variants/options
- imagery/media references
- included items
- delivery/returns/warranty facts
- claims exactly as source claims them, marked unverified until reconciled
- real review/proof references where available
- existing brand/layout signals
- traffic-source hook/promise/offer where applicable.

## Output
```yaml
source_packet:
  sources: []
  product_facts: []
  offer_facts: []
  logistics_facts: []
  proof_candidates: []
  media_candidates: []
  source_claims_unverified: []
  brand_signals: []
  campaign_signals: []
```

## Prohibited
- copying competitor prose as final copy
- upgrading supplier claims to VERIFIED
- inferring warranty/stock/commission from vague marketing text.

---

# 2. CONTEXT BRIEF AGENT

## Goal
Convert research/evidence into the smallest complete commercial brief.

## Inputs
- source packet
- AFFINITY decision object
- canonical market intelligence
- traffic/campaign context.

## Required output
```yaml
context_brief:
  market:
  locale:
  product_or_offer:
  audience:
  traffic_source:
  awareness_stage:
  purchase_mode:
  core_pain:
  core_desire:
  quick_win:
  mechanism:
  primary_objection:
  secondary_objections: []
  verified_claims: []
  supported_claims: []
  prohibited_claims: []
  economics:
  logistics:
  warranty_returns:
  target_action:
```

## Quality rule
Every field must matter to page construction. Do not pad the brief with generic personas or invented psychographics.

---

# 3. BRAND / STORE DNA AGENT

## Goal
Create a reusable identity object so generated pages look native to the brand/store instead of like isolated templates.

## Inputs
- existing site/store where available
- supplied brand kit
- existing page examples
- market/product context.

## Output
```yaml
brand_store_dna:
  id:
  brand_voice:
  visual_personality:
  primary_colors: []
  neutral_colors: []
  typography_character:
  logo_usage:
  image_style:
  icon_style:
  radius_rule:
  surface_rule:
  shadow_rule:
  cta_rule:
  motion_rule:
  content_density:
  layout_rhythm:
  locale_rules:
  inherited_from_existing_brand: true|false
```

## Rules
- Existing validated brand identity wins by default.
- A new art direction requires an explicit experiment/creative rationale.
- Do not infer exact fonts/colors from low-confidence evidence when a supplied brand kit exists.

---

# 4. DECISION-BARRIER AGENT

## Goal
Determine what prevents this specific visitor from taking the target action.

## Barrier classes
- relevance
- problem recognition
- solution understanding
- differentiation
- economic justification
- credibility
- risk
- compatibility
- action friction
- post-purchase uncertainty.

## Output
```yaml
decision_barriers:
  - id:
    class:
    severity: 1-10
    evidence:
    resolution_needed: true|false
    preferred_section_roles: []
```

## Rule
No section should exist without resolving a material barrier or delivering promised content value.

---

# 5. ANGLE MATRIX AGENT

## Goal
Select the best evidence-backed persuasive entry point.

## Candidate classes
- pain point
- desired outcome
- economic savings
- time savings
- labor reduction
- convenience
- premium quality
- speed
- risk reduction
- local scarcity when verified
- price/value gap
- technical superiority when verified
- ease of use
- professional ROI
- social proof when genuine
- offer-led
- seasonal
- segment-specific
- comparison.

## Score each candidate
```yaml
angle:
  id:
  class:
  statement:
  relevance_to_traffic: 0-10
  pain_or_desire_strength: 0-10
  evidence_strength: 0-10
  differentiation: 0-10
  visual_demonstrability: 0-10
  economic_strength: 0-10
  trust_risk: 0-10
  total_score:
```

## Rule
The chosen angle must maximize fit and evidence, not drama.

---

# 6. MESSAGE-MATCH AGENT

## Goal
Make destination continuity explicit for paid/email/social/campaign traffic.

## Output
```yaml
message_match:
  required:
  source_hook:
  source_problem:
  source_promise:
  source_offer:
  source_visual_theme:
  landing_headline:
  landing_supporting_message:
  proof_required: []
  cta_continuity:
  mismatch_risks: []
```

## Rule
If two traffic sources require materially different promises, create separate variants rather than one compromised hero.

---

# 7. ARCHETYPE AGENT

## Goal
Choose page family before choosing components.

## Inputs
- context brief
- decision barriers
- angle
- message match
- media availability
- economics/trust burden.

## Output
```yaml
archetype_decision:
  selected:
  rationale:
  required_roles: []
  optional_roles: []
  rejected_archetypes:
    - name:
      reason:
```

## Rule
Use the shortest persuasive architecture that fully resolves the material decision barriers.

---

# 8. LAYOUT DNA AGENT

## Goal
Create/choose a persistent reusable layout object analogous to a governed template, without copying vendor templates.

## Output
```yaml
layout_dna:
  id:
  version:
  archetype:
  brand_store_dna_id:
  default_section_order: []
  required_roles: []
  optional_roles: []
  design_token_profile:
  mobile_overrides:
  conversion_action_model:
  default_for_scope: false
  parent_layout_id:
```

## Reuse rules
- Prefer an existing strong layout DNA for similar product/audience conditions.
- Duplicate/version a layout before materially altering it.
- Never silently mutate a winning layout shared by live pages.

---

# 9. COMPONENT PLANNER / SCORER

## Goal
Map each required page role/barrier to the best registry component.

## Scoring dimensions
- objective fit
- awareness fit
- decision-barrier fit
- evidence readiness
- media readiness
- mobile fit
- performance cost
- brand fit
- traffic fit.

## Output
```yaml
component_plan:
  - order:
    role:
    barrier_ids: []
    candidate_components:
      - id:
        score:
        reasons: []
    selected_component_id:
    selection_reason:
    required_inputs: []
    evidence_ids: []
    custom_component_required: false
```

## Rules
- Default minimum recommended score: 70/100.
- Never choose a component whose proof requirements cannot be met.
- If two sections solve the same barrier with similar content, keep the stronger one.
- New custom components require the Component Creation Rule in the Page Engine.

---

# 10. COPY AGENT

## Goal
Write to component slots and word budgets.

## Inputs
- selected component ID and metadata
- angle/message match
- verified/supported claim set
- brand voice
- locale.

## Output
```yaml
component_copy:
  component_id:
  slots:
    eyebrow:
    headline:
    supporting_copy:
    bullets: []
    cta:
    microtrust:
  claim_ids_used: []
  prohibited_claim_check: PASS|FAIL
```

## Rules
- Use benefit language only when the causal bridge from feature/spec to buyer outcome is defensible.
- No unsupported superlatives.
- No fake social proof, urgency, scarcity or percentages.
- Avoid repeating the same claim across multiple sections unless repetition serves a distinct decision point.

---

# 11. MEDIA AGENT

## Goal
Choose/generate media with explicit purpose and provenance.

## Output
```yaml
asset_manifest_item:
  asset_id:
  section_component_id:
  purpose:
  asset_type:
  source_type:
  source_ref:
  rights_or_provenance:
  product_fidelity: exact|high|contextual|decorative
  aspect_ratio:
  mobile_crop:
  generated: true|false
  documentary_proof: false
  warnings: []
```

## Rules
Source priority:
1. user supplied
2. manufacturer/merchant verified
3. licensed/owned
4. reference-conditioned generation
5. contextual generation.

Generated media cannot be used as documentary customer proof, real before/after evidence, real certification evidence or exact demonstration of unverified performance.

---

# 12. DESIGN TOKEN AGENT

## Goal
Turn brand/layout intent into deterministic visual rules.

## Output must cover
- container width
- gutters
- section spacing
- typography scale
- line length
- colors
- surface system
- borders/radius
- elevation/shadows
- CTA hierarchy
- focus states
- image crop rules
- motion budget
- breakpoints.

## Rule
No section-level random styling that violates the shared token system.

---

# 13. BUILDER AGENT

## Goal
Implement the approved Page DNA faithfully in the existing project stack.

## Inputs
- Page DNA
- Layout DNA
- component plan
- component copy
- asset manifest
- design tokens
- build handoff contract.

## Rules
- Do not redesign strategy during coding.
- If implementation constraints invalidate a component, return to planner with the exact constraint.
- Preserve IDs in code/data attributes where useful for analytics and QA.
- Reuse existing stack and accessible primitives.
- Avoid adding dependencies for trivial visual effects.

---

# 14. QA AGENT

## Goal
Audit rendered experience, not just source code.

## Required passes
- truth/claims
- message match
- component completeness
- duplicate/repetitive content
- mobile/responsive rendering
- accessibility
- performance
- media fidelity/provenance
- CTA destination/tracking
- SEO/metadata where relevant
- analytics instrumentation
- experiment isolation.

## Output
```yaml
qa:
  score:
  hard_failures: []
  warnings: []
  viewport_results: []
  performance_results:
  accessibility_results:
  link_results:
  result: PASS|FAIL
```

Minimum default score: 85/100 and zero hard failures.

---

# 15. VARIANT AGENT

## Goal
Create controlled experiments instead of random redesigns.

## Output
```yaml
variant:
  parent_page_id:
  variant_id:
  primary_hypothesis:
  locked_fields: []
  changed_fields: []
  expected_behavior_change:
  primary_metric:
  guardrail_metrics: []
  seo_duplicate_strategy:
```

## Rule
Prefer one primary hypothesis per variant.

---

# 16. LEARNING AGENT

## Goal
Turn measured outcomes into conditional rules.

## Output
```yaml
learning_record:
  product_class:
  audience:
  traffic_source:
  awareness_stage:
  angle:
  archetype:
  component_sequence: []
  locale:
  device:
  baseline:
  result:
  RPV_change:
  confidence:
  disposition: KEEP|ITERATE|ROLLBACK|INSUFFICIENT_DATA
  reusable_lesson:
```

## Rule
Never generalize “component X converts” from a single page. Learn only the conditional relationship between component/sequence and context.

---

# 17. FAILURE / FALLBACK CONTRACTS

When proof is missing:
- replace social proof with factual/specification/merchant/logistics proof;
- do not create synthetic proof.

When exact product imagery is weak:
- use verified imagery even if less polished;
- generated contextual imagery may supplement but not replace exact product identity.

When data is stale:
- show freshness/uncertainty internally;
- re-check before launch;
- do not publish volatile claims as current.

When component fit is low:
- simplify the page;
- create a custom component only if the need is repeatable and justified.

When the page becomes long:
- map every section back to a barrier;
- remove duplicate sections before shortening copy mechanically.

---

# 18. MASTER EXECUTION INSTRUCTION

Use this condensed instruction for page-producing agents:

> Operate under AFFINITY Page Engine governance. Do not generate a page directly from the user's raw prompt or product URL. First normalize sources into verified facts, create the buyer/context brief and Brand/Store DNA, identify material decision barriers, score/select the strongest evidence-backed angle, preserve campaign message match, choose an archetype and reusable Layout DNA, create valid Page DNA, score/select registry components, then generate component-level copy and a provenance-aware media plan under shared design tokens. Build mobile-first in the existing stack, preserve component/experiment IDs, and run rendered QA for claims, fidelity, accessibility, Core Web Vitals, responsive behavior, tracking and analytics. Use controlled parent/variant experiments and feed measured RPV back into conditional angle/archetype/component learning. Never fabricate proof, urgency, scarcity, commercial facts or tracking.
