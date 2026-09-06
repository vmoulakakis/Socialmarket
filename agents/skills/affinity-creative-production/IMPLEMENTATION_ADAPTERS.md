# AFFINITY Page/Site Engine — Implementation Adapter Contract

Version: 1.0
Status: Canonical

Purpose: keep Page/Site DNA and component intelligence portable across stacks without forcing every website into one React component library.

---

## 1. Principle

AFFINITY component IDs are **semantic contracts**, not framework-specific source files.

Example:

`AF-S27 Economic Comparison`

may be implemented as:
- a React/Next component in a Next.js application,
- a Shopify section/block in a commerce theme,
- semantic HTML/CSS in a static microsite,
- an Astro component,
- native blocks in Webflow/another builder.

The semantic job, evidence rules, copy slots, responsive behavior, analytics and QA remain constant even when implementation changes.

This prevents framework lock-in while preserving conversion-system consistency.

---

# 2. Adapter types

Canonical adapters:

- `next-react`
- `shopify-theme`
- `astro-static`
- `vanilla-static`
- `builder-native`
- `existing-custom-stack`

Choose the adapter from the existing project. Never migrate frameworks solely to use AFFINITY components.

---

# 3. Adapter interface

Every adapter must support:

```yaml
adapter:
  id:
  stack:
  supports:
    page_dna:
    site_dna:
    component_registry:
    design_tokens:
    asset_manifest:
    analytics_ids:
    localization:
    experiments:
  component_mapping:
  global_component_mapping:
  unsupported_components: []
  fallback_policy:
  build_command:
  test_command:
  deploy_adapter:
```

---

# 4. Component implementation manifest

Each actual component implementation should register:

```yaml
implementation:
  semantic_component_id: AF-S27
  adapter_id: next-react
  implementation_id: AF-S27.next-react.v1
  source_path: components/affinity/EconomicComparison.jsx
  version: 1
  status: stable
  input_contract:
  responsive_contract:
  accessibility_contract:
  analytics_contract:
  dependencies: []
  performance_notes:
  tested_viewports: []
```

Several visual implementations may map to one semantic ID:

- `AF-S27.next-react.v1`
- `AF-S27.next-react.v2`
- `AF-S27.shopify.v1`

The Page Engine selects the semantic role first. The adapter selects a compatible implementation second.

---

# 5. Visual variants are not new semantic components by default

A component gets a new semantic ID only when its communication/conversion job materially differs.

Changes such as:
- background treatment
- border style
- alignment
- image side
- typography treatment
- card surface

usually remain visual implementation variants under the same semantic component ID.

This prevents registry inflation and makes experiments interpretable.

---

# 6. Next.js / React adapter

Default behavior when an existing project uses Next.js/React:
- preserve App Router/project conventions
- prefer server components for static content where appropriate
- use client components only for interaction
- reuse project CSS/Tailwind/design primitives
- use accessible primitives already installed
- preserve image optimization strategy
- keep component props data-driven from Page DNA/content objects
- expose semantic `data-affinity-component` IDs where useful for QA/analytics.

Example conceptual rendering:

```jsx
<Section
  data-affinity-component="AF-S27"
  data-page-id={pageId}
  data-variant-id={variantId}
>
  ...
</Section>
```

Do not leak internal metadata visually to users.

---

# 7. Shopify adapter

When the destination is Shopify:
- use native theme sections/blocks/metafields where practical
- preserve product/variant/cart/checkout truth from Shopify
- do not recreate checkout
- map registry components to theme sections/blocks
- support theme editor reordering/editing when feasible
- store Brand/Store DNA in theme settings/tokens where appropriate
- keep product data dynamic
- avoid duplicated hard-coded catalog facts.

PagePilot-derived concepts such as reusable layouts, product blocks, product sections and cart drawer functionality are implemented through native Shopify primitives when that is the target stack.

---

# 8. Static / Astro adapter

For content-heavy or campaign experiences:
- semantic HTML first
- minimal JavaScript
- progressive enhancement
- static generation where possible
- lightweight interactive islands only when justified
- CSS variables/design tokens
- data-driven repeated component structures.

Do not add React merely because the registry was designed conceptually around components.

---

# 9. Builder-native adapter

For Webflow/Lovable/other supported builders:
- preserve builder-native components/classes/variables
- translate semantic component IDs to builder primitives
- preserve IDs in implementation metadata/naming when possible
- use the builder's native responsive and CMS systems
- do not reconstruct the property in another stack unless explicitly justified.

If a builder cannot express a required interaction or semantic component safely, record the unsupported component and choose a registry fallback.

---

# 10. Fallback policy

When an implementation is unavailable:

1. do not silently drop the decision barrier;
2. find another registry component serving the same role;
3. recalculate component suitability;
4. if no adequate option exists, create a minimal custom implementation under the Component Creation Rule;
5. register the new implementation only after QA.

The fallback must preserve the communication/conversion job, not visual similarity.

---

# 11. Adapter selection

Selection priority:

1. existing production stack
2. native platform primitives
3. existing reusable project components
4. AFFINITY adapter implementation
5. minimal custom component.

Never choose a stack because it looks fashionable.

---

# 12. Implementation maturity

Statuses:
- `experimental`
- `tested`
- `stable`
- `deprecated`
- `retired`.

Promotion to `stable` requires:
- functional pass
- required viewport pass
- accessibility basics
- performance acceptance
- claim/media rules satisfied
- analytics mapping
- at least one successful production use.

A conversion win is not required to call code stable; code stability and commercial performance are different dimensions.

---

# 13. Component implementation learning

Track separately:

```yaml
implementation_performance:
  semantic_component_id:
  implementation_id:
  adapter_id:
  context:
  impressions:
  interactions:
  downstream_conversion:
  RPV:
  performance_cost:
  accessibility_issues:
  disposition:
```

This allows AFFINITY to learn that two implementations of the same semantic job perform differently without confusing visual implementation with page strategy.

---

# 14. Global component adapters

Site DNA global components—header, navigation, search, cart, footer, disclosure, consent—must use the platform's strongest native patterns where possible.

Examples:
- Shopify native cart infrastructure
- Next.js existing navigation shell
- CMS/builder native menus
- platform-localized route handling.

Do not force a generic AFFINITY header implementation into every property.

---

# 15. Definition of “all components”

For AFFINITY, “all components available to the intelligence layer” means every semantic registry component is selectable by the Page Engine.

It does **not** mean every semantic component must have hand-written implementations in every framework before the system can operate.

An adapter must either:
- map the semantic component to an existing implementation,
- map to a known fallback serving the same job, or
- create/register a project-local implementation.

This is the scalable model for hundreds of components across heterogeneous sites.

---

# 16. Builder handoff requirement

`BUILD_HANDOFF.schema.json` should identify:
- target repository/project
- framework/adapter
- semantic component plan
- expected source paths where known
- dependencies allowed/forbidden
- asset manifest
- design tokens
- QA acceptance.

The builder owns implementation quality, not commercial strategy.

---

# 17. Final rule

**Semantic intelligence is global; rendering is local.**

AFFINITY owns what a component must accomplish. The implementation adapter owns how that job is rendered correctly in the project's native stack.
