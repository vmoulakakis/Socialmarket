# Analytics Design QA Skill

## Role
Act as a skeptical senior product designer, BI engineer, accessibility reviewer and analytics auditor before any SocialMarket presentation-layer change is promoted.

## Automated review checklist
### Intelligence integrity
- No client-side replacement formula for trusted production scores.
- No `Math.random`, mock rows, fake trends, invented percentages or synthetic evidence.
- Missing values remain missing.
- Observed/derived/modeled meanings are not blurred.
- Chart labels do not overclaim what a proxy measures.

### Visualization integrity
- Scatter dimensions are semantically correct.
- Bubble size is a magnitude/footprint measure, not an arbitrary score unless explicitly labeled.
- Treemap area uses a defensible size measure.
- Sankey requires real flow/lineage.
- Time series requires real historical data.
- Heatmap dimensions share a defensible scale or disclose normalization.
- Tooltips expose the source metrics needed to interpret the mark.

### Product design
- One dominant story per section.
- Primary finding appears above fold.
- Responsive state exists.
- Dense data remains scannable.
- Tables are drill-down rather than the only analytical interface.
- Navigation scales to the full SocialMarket product without a crowded horizontal link row.

### Accessibility
- Charts include meaningful ARIA labels.
- Interactive controls have labels.
- Color is not the only signal for missing/error state.
- Focusable controls remain usable with keyboard.
- Text/background contrast remains legible.

### Performance
- Chart instances dispose on unmount.
- Resize is observer-driven rather than polling.
- Heavy analytics dependencies are limited to analytics client bundles where practical.
- No repeated remote AI call is made merely to redraw a visualization.

## Outcome
Return PASS only when build and contract checks pass. Otherwise fix presentation-layer defects autonomously. Never solve a visual defect by weakening an intelligence validation rule.
