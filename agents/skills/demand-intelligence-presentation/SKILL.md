# Demand Intelligence Presentation Skill

## Purpose
Make Demand Intelligence the flagship analytical experience of SocialMarket while preserving the existing semantic market truth.

## Required source contract
Primary source: `admin_dashboard_snapshot` and its trusted `category_market`, `pain_gaps`, merchant/product context.

Do not create alternative client-side demand, competition, pain, opportunity, or confidence formulas.

## Core business questions
Every Demand screen should help answer, in order:
1. Where is demand strongest?
2. Where is demand both strong and commercially less crowded?
3. What evidence supports that conclusion?
4. What validated pain explains the demand?
5. Which merchant/product environment can monetize it?
6. What is missing or too weak to act on?

## Required visual modules
### Opportunity landscape
Scatter/quadrant:
- X = existing competition score.
- Y = existing demand score.
- Bubble size = evidence footprint when available.
- Color = existing opportunity score when available.
- Exclude rows missing either demand or competition.

### Signal matrix
Heatmap of existing comparable 0–100 dimensions such as demand, competition, pain, opportunity and confidence converted only for display from 0–1 to percentage when that is the actual storage scale.

### Evidence footprint
Treemap or equivalent only when size is a count/footprint measure. Explicitly label it as evidence footprint; never call an index-based area market size.

### Pain landscape
Show only validated pain gaps. If zero, explain that the audit gate is protecting the pipeline.

### Trend explorer
Render only when the data source exposes historical comparable observations. Until then, show a fail-closed state stating that no synthetic trend is drawn.

### Lineage / Sankey
Render only with actual entity-level linkage or flow. Stage inventory counts MUST NOT be presented as a Sankey conversion flow.

### Auditable grid
Every visual must resolve to the underlying production rows. Sorting/filtering is encouraged. Missing stays visible as an em dash or explicit missing state.

## Narrative format
Use presentation-quality story order:
- headline finding;
- opportunity landscape;
- drivers;
- evidence concentration;
- pain context;
- missing-data blockers;
- auditable rows;
- AI interpretation.

## AI analyst rule
The AI analyst may interpret the current production snapshot and recommend actions, but must not fill missing demand, competition, search volume, CVR, EPC, conversion, or pain evidence. It receives the same trusted rows shown by the UI.

## Autonomous correction loop
After implementation:
- run production build;
- run design contract validation;
- inspect failures;
- fix code without weakening truth gates;
- repeat until green or report the exact external blocker.
