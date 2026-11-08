---
version: alpha
name: "SocialMarket AI — Evidence-First Command Center"
colors:
  background: "#070b13"
  surface: "#0c111c"
  surfaceSecondary: "#111827"
  surfaceTertiary: "#151e2e"
  text: "#f5f7fb"
  muted: "#8d9aae"
  action: "#8b5cf6"
  evidence: "#22d3ee"
  positive: "#34d399"
  caution: "#fbbf24"
  negative: "#fb7185"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
  data:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
rounded:
  panel: "18px"
  control: "9px"
  item: "14px"
components:
  shell:
    purpose: "Persistent navigation with canonical pipeline context"
  sourcePanel:
    purpose: "Evidence, provenance and model confidence in one view"
  canonicalWorkspace:
    purpose: "Accessible listing/inspecting of real records"
omitted:
  - section: spacing
    reason: "Existing stylesheet and CSS module spacing values are preserved."
---

# SocialMarket AI — DESIGN.md

## Overview

**Register:** Private admin intelligence product, not an affiliate landing page. **User:** an operator evaluating merchant eligibility, demand, product evidence, curation and publishing-intent state.

**North Star:** A sober operational evidence console. Information must distinguish a source record, audited business insight, forecast, AI selection and verified external action. Never imply an imported offer is an AI-selected product, a stored job is a posted social update, or unknown stock is zero stock.

**Signature:** A visible sequence Demand → Merchant verification → Product evaluation → Creative review → Approved publishing intent, with direct drill-down to actual source evidence. Do not replace it with generic marketing hero cards.

**Canonical runtime owner:** `app/design-v2.css` owns the shared `--sm-*` theme variables; `app/globals.css` and `app/semantic.css` own legacy/base structures. `components/CanonicalWorkspace.module.css` owns scoped listings. Do not create duplicate theme systems.

## Colors

The current dark-first tokens are preserved, including background `#070b13`, surfaces `#0c111c` / `#111827`, text `#f5f7fb` and evidence cyan `#22d3ee`. Emerald indicates a positive verified state, amber a warning, and red an error. Color must never be the sole carrier of an action's meaning. The 2026-11-08 work adds a cyan focus outline only to the canonical workspace.

## Typography

Use the established Inter/system font stack with reliable Greek glyph fallback. Prefer readable numeric typography, tabular alignment for evidence metrics, and monospace only for IDs/technical markers. Do not install fonts until their Greek coverage and site bundle impact are verified.

## Layout

Navigation/sidebar: retain `AppShell` and its existing collapsible/mobile behavior. Data: keep real back-end pagination, filters, sorting and permission boundaries, not fictional front-end data. CanonicalWorkspace: scoped 1440px max-width and mobile layout stay unchanged; its new rules only improve focus visibility, wrap long content and allow compact metrics/actions to reflow on smaller screens.

Check 320, 390, 768, 1024 and 1440 CSS px, zoom and keyboard/focus order before any merge. Preserve content and scroll ownership, including long details JSON and wide data tables.

## Elevation & Depth

Compact borders indicate distinct evidence groups; shadows stay subtle. Prioritize actual data density, load/error/retry states and crisp screen-reader information over cinematic effects. Any hover improvement must be optional and never hide an action from touch users.

## Shapes

Existing 9–18px radii are maintained according to component responsibility. Avoid making controls visually consistent by rewriting their interaction or validation models.

## Components

- **Navigation:** Preserve every existing section and href.
- **Control Tower:** Keep canonical API health values and explicit unknown states. Do not infer operational GREEN from one ready deployment.
- **CanonicalWorkspace:** Keep section names, data fetching, keyboard navigation, retries, pagination, image handling, product tracking URLs, open-post links and JSON details intact.
- **Cards/KPIs:** Only show data from VMDB or trusted sources; format missing values as missing.
- **Affiliate actions:** Preserve original full tracking URLs including Linkwise parameters and `rel="sponsored noopener noreferrer"`; never rebuild or shorten a link without source validation.
- **Focus:** Visible cyan outline on actionable elements; forced-colors fallback.
- **Motion:** An unobtrusive border-color change on hover; disabled under reduced-motion preference.

## Do's and Don'ts

**Do:** Keep approved SocialMarket model/router policies, Supabase data contracts, merchant verification rules, genuine offer provenance and the SocialScheduler outbox separation. Preserve noindex/admin protection and all observable controls. Run the existing extensive CI + actual browser smoke tests before approval.

**Don't:** Import a full template or Tailwind for a CSS-only enhancement, rename API fields, change the commission rule, assume unverified stock is in stock, modify affiliate links or publish/merge unreviewed changes.

## 2026-11-08 Change Scope

The first change touches only `components/CanonicalWorkspace.module.css`, a CSS module loaded by the existing CanonicalWorkspace. This file documents the existing design system. Neither JS/JSX, APIs, queries, calculations, business policy nor publishing integrations are changed. Production remains on `main` revision `b282d8e74832ef7566f6667a6b1f247bc7cffbdb`. Review the full pipeline CI and actual responsive screenshots before any merge.
