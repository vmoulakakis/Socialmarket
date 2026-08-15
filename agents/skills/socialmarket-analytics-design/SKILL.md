# SocialMarket Analytics Design Skill

## Mission
Turn trusted SocialMarket intelligence into presentation-grade, interactive business analytics without changing the underlying intelligence semantics.

This skill governs the presentation layer only. It MUST NOT redefine demand, competition, pain, merchant trust, product opportunity, affiliate economics, confidence, audit state, or forecast semantics.

## Autonomous operating mode
Operate autonomously unless the user explicitly intervenes.

For every analytics screen:
1. Inspect the production data contract and identify which fields are observed, derived, modeled, or missing.
2. Choose the visual form that best answers the business question; never force the data into a predetermined template.
3. Build the visual and interaction layer.
4. Run design-contract validation and production build.
5. Fix build errors, misleading encodings, inaccessible states, overflow, or semantic ambiguity before proposing promotion to production.
6. Preserve fail-closed states. If a visual needs unavailable data, render an explicit analytical empty state rather than synthetic data.

## Presentation-grade composition
Treat each major section like a strong executive presentation slide that happens to be interactive.

Required hierarchy:
- one primary analytical question;
- one headline finding grounded in existing metrics;
- one dominant visual;
- evidence/context immediately adjacent;
- implication/action only when supported;
- drill-down to auditable rows.

Avoid wallpaper dashboards made from equally weighted cards.

## Visual grammar
Use:
- large narrative headlines for the main conclusion;
- bento-style grouping only when groups have different analytical roles;
- full-width charts for primary relationships;
- heatmaps for multidimensional comparison;
- scatter/quadrants for demand versus competition;
- treemaps only for additive/footprint measures, never arbitrary index-as-market-size claims;
- Sankey only when actual entity-level lineage or flow exists;
- time series only when real historical timestamps and comparable observations exist;
- tables as audit/drill-down layers, not as the primary story.

## Semantic color contract
- Violet: AI/derived intelligence.
- Cyan: evidence/data.
- Emerald: validated/profitable/healthy.
- Amber: modeled/incomplete/caution.
- Red: operational risk/failure.
- Neutral slate: missing, unavailable, context.

Color MUST NOT turn a missing metric into an implied favorable state.

## Truth contract
Non-negotiable:
- Missing is not zero.
- Network observed is not first-party observed.
- Modeled is not observed.
- Confidence is not probability unless explicitly defined that way by the source contract.
- Demand proxy is not search volume.
- Competition proxy is not keyword difficulty.
- Opportunity score must be displayed as the existing score, not silently recomputed in the UI.
- No mock, demo, random, decorative, or interpolated business data in production analytics.

## Interaction contract
Prefer interactions that answer real questions:
- filter by category/subcategory;
- hover for source metrics;
- sort audit tables;
- compare comparable entities;
- explain with the AI analyst using the same production snapshot;
- drill to evidence where available.

Avoid interaction for decoration.

## Technical stack
Preferred presentation stack:
- Next.js / React for production UI;
- Apache ECharts for multidimensional analytical visuals;
- TanStack Table for auditable analytical grids;
- Motion for restrained state/layout transitions;
- Supabase RPC/views remain the production truth source.

External design/analytics tools such as Figma or MotherDuck may be used as design/analysis laboratories, but they MUST NOT become a competing source of truth.

## Design quality bar
The interface should feel like a premium decision-intelligence product, not a generic AI admin dashboard. It should combine the narrative clarity of a high-end strategy presentation with the density and auditability of a modern BI terminal.

## Completion gate
A screen is not complete until:
- production build passes;
- design contract test passes;
- all missing-data states are explicit;
- no metric semantics changed;
- mobile/responsive behavior is defined;
- primary insight is understandable without reading a table;
- every visualization can be traced back to production data fields.
