# SocialMarket — Top 30 Opportunities Creative Campaign

Production batch generated 2026-08-11 from the workbook `Top Opportunities` sheet.

## Rules
- 30/30 products have a dedicated 1080x1350 creative.
- Every QR encodes the **exact full Linkwise tracking URL** from the source workbook.
- QR payloads were machine round-trip decoded before packaging.
- `/go/<slug>` routes redirect to the same Linkwise tracking URLs and are intended only as human-readable short paths.
- Live price/stock validation is kept as audit metadata and does not remove an item from the creative batch.
- Product-photo provenance is classified as `MODEL_FAMILY`, `MODEL_REFERENCE`, or `STYLE_REFERENCE`; non-exact visuals must be verified against the exact SKU before paid publishing.

## Canva
A 30-page editable Canva design was created from the production bundle. Text, product visual, CTA, price treatment, QR and short-path labels are structured per page.

## Tracking integrity
Do not replace QR payloads with merchant URLs. The QR must continue to encode the original `go.linkwi.se` URL so Linkwise attribution remains intact.
