# Back-to-School 2026 Greece — Evidence Ledger

Research snapshot: 2026-08-13 (Europe/Athens)

## Decision rule
A promotional winner must simultaneously pass:
1. price > €50
2. validated high-demand pain/solution
3. low exact-SKU / feature-combination competition in Greece
4. high offline scarcity (no easy major-chain/store-pickup substitute)
5. acceptable product quality evidence
6. defensible real deal / price advantage
7. live stock / sufficient campaign runway
8. usable affiliate/deeplink route

**No product is promoted merely because it has a large crossed-out discount or high affiliate EPC.**

## Data integrity findings

### Linkwise snapshot
- `linkwise-products.json` Drive artifact is 3,837,648,460 bytes but terminates with malformed/premature JSON EOF.
- 2,668,657 complete product objects are recoverable before the malformed tail.
- The tolerant research parser may use those complete objects but must mark the scan as salvaged/incomplete.
- The July snapshot's `valid_to` field is too stale/short-runway to be used as a discovery hard gate: the first strict BTS run excluded ~1.07M otherwise >€50 records on validity alone.
- A separate demand-first scan found 1,071,919 records >€50 but only 1,912 with `times_bought >= 3`; the apparent BTS hits were false positives. Therefore the snapshot does not provide representative BTS first-party purchase counts.

### Discount semantics
The raw feed `discount` field is not consistently a percentage. Example Cilek ACC-8483: price €130, full price €225, raw `discount=95`. This represents a €95 absolute difference; the verified percentage is `(225-130)/225 = 42.22%`.

Policy: when `price` and `full_price` exist, always recompute the percentage and keep the raw field only for audit.

---

## Validated market pain: grow-with-child ergonomics

### Demand baseline
The broad Greek market clearly buys adjustable child study furniture. Brateck B301 has strong Greek engagement/review evidence and wide seller distribution; this validates the need but also proves that generic adjustable desk/chair sets are **not** low competition.

### Feature gap
The more defensible gap is not “child desk/chair” generically. It is advanced fit/ergonomics: seat/back adjustment, child-size fit, foot support, appropriate caster behaviour, tilt/storage where relevant, and products that grow with the child.

IKEA VIMUND is used only as a major-retailer feature benchmark, not a source product.

---

## Candidate ledger

### 1. La Redoute JIMI school desk + bench — CONDITIONAL / BEST CURRENT NEAR-WINNER

**Product:** Bureau + banc écolier Jimi / Σχολικό παιδικό γραφείο + σκαμπό JIMI  
**Merchant:** La Redoute Greece  
**Affiliate:** Linkwise program 23  
**Greek current category price observed:** €165.60 from €207 (-20%); Greek site also displays the 30-day low-price field.  
**Product demand/quality:** 4.3/5 from 50 authenticated reviews across La Redoute locales; design 4.8, practical 4.3, 83% recommendation on the French product page.  
**Pain:** compact child study station with matching bench and storage under worktop.  
**Exact Greek competition:** BestPrice currently indexes the exact product essentially from La Redoute; exact private-label seller breadth is low.  
**Offline:** La Redoute has one 550 m² showroom in Chalandri with a Kids Section and selected home products. The company explicitly says customers must call to verify whether a particular product is displayed. Exact JIMI showroom presence is therefore **unknown**, not absent. Online orders are normally delivered to the declared address; BOX NOW is limited to fashion/linen, not furniture.  
**Deal concern:** the Greek €165.60 is a real local -20% offer, but the same JIMI product is currently discounted more deeply in France/Belgium. Regional promotions differ, so this does not invalidate the Greek discount, but it weakens any “exceptional deal” claim.  
**Decision:** **CONDITIONAL**. Passes demand + exact low competition + affiliate. Needs exact Greek stock confirmation and exact showroom-display confirmation; deal is good, not exceptional.

Key sources:
- https://www.laredoute.fr/ppdp/prod-529091000.aspx
- https://www.laredoute.gr/spiti/epipla/paidiko-ypnodomatio/paidika-grafeia/paidika-grafeia_s-97418.aspx
- https://www.bestprice.gr/cat/7885/paidika-grafeia/f/1_31995/la-redoute.html
- https://www.laredoute.gr/el-gr/landing-new/2527/
- https://www.laredoute.gr/resources/faq

### 2. Vipack Comfortline 201 adjustable desk + chair — STRONG GAP / FAILS DEAL

**Product:** Vipack Comfortline 201 adjustable child desk + chair  
**Merchant:** vidaXL Greece  
**Affiliate:** Linkwise program 14113; commission ~6.15%; valid deeplink generator available.  
**Greek price observed:** €214.99.  
**Pain/fit:** explicitly ergonomic and height-adjustable; desk and chair grow with child, age 3–10.  
**Demand:** the underlying grow-with-child pain is strongly validated in Greece; Comfortline family has meaningful external review/ranking evidence.  
**Exact Greek competition:** exact EAN 5420070224147 appears unusually narrow in Greece, led by vidaXL.  
**Deal:** weak. Current Greek price is not a compelling price advantage versus available European prices/history.  
**Decision:** **REJECT FOR PROMOTION AT CURRENT PRICE; retain as gap benchmark**.

Key source:
- https://www.vidaxl.gr/e/vipack-grafeio-paidiko-comfortline-201-rythmizdomeno-rozdleyko-karekla/5420070224147.html

### 3. Mark Adler Junior 3.6 ergonomic child chair — MARKET-GAP BENCHMARK / NO AFFILIATE

**Features:** height adjustment, back-height/depth adjustment, footrest, foldable arms, child-focused fit and safety casters.  
**Greek seller breadth:** around 2–3 sellers depending colour; best observed price about €109.90.  
**Why interesting:** much closer to the advanced ergonomic feature gap than generic children’s office chairs.  
**Affiliate:** the low-price sellers checked (E-Dructer, Homelutions) are not in the current Linkwise program universe.  
**Decision:** **BENCHMARK ONLY** until an equivalent affiliate SKU is found.

### 4. La Redoute Adil — HIGH DEMAND / QUALITY & DEAL CONCERNS

**Demand:** 297 authenticated reviews, ~4.1/5.  
**Greek sale:** €194.40 from €243 (-20%) in the Greek children’s desk category.  
**Competition:** exact private-label SKU has low Greek seller breadth.  
**Quality:** repeated verified complaints include damaged panels/finish, difficult assembly and occasional stability/odour issues.  
**Deal:** French pricing is currently materially lower in some colours/promotions.  
**Decision:** **REJECT / LOW PRIORITY** despite demand.

Source:
- https://www.laredoute.fr/ppdp/prod-528977089.aspx

### 5. La Redoute Nadil — GOOD QUALITY DEMAND / FAILS DEAL

**Evidence:** 14 authenticated reviews, about 4.6/5; explicitly suited to small bedrooms.  
**Issue:** Greek current price observed around €224 while French promotional pricing is materially lower.  
**Decision:** **REJECT FOR CURRENT DEAL**.

### 6. La Redoute Zag — MODERATE QUALITY ONLY

**Evidence:** about 3.8/5 from 17 reviews; compact child use is relevant, but there are complaints around size expectations, fragility and leg stability.  
**Decision:** **REJECT / insufficient quality confidence for a hidden-product campaign**.

### 7. vidaXL child drawing desk 287447 — REJECT

**Greek price:** €196.99.  
**Fit:** adjustable/tilting worktop, storage, child study/drawing use.  
**Quality:** external review evidence is mixed/weak (~3.3/5 in a sizeable review set).  
**Deal:** Greek price materially above observed European vidaXL prices.  
**Decision:** **REJECT quality + deal**.

### 8. vidaXL folding wall desk 100×60 — GAP IDEA, NOT HIGH-DEMAND WINNER YET

**Fit:** folds to ~8 cm from wall; useful for very small study spaces.  
**Greek price:** around €104–107 depending colour; one observed colour had only ~9% discount versus 30-day non-promotional price.  
**Competition:** some exact vidaXL wall-desk SKUs are already syndicated across many Greek sellers; this varies by model.  
**Demand:** current evidence is weaker than for grow-with-child furniture.  
**Decision:** **RESEARCH ONLY**. Do not promote until a specific SKU proves both demand and low seller breadth.

### 9. CONNETIX Pastel Creative Pack 120 — REJECT

**Demand/quality:** excellent external reviews.  
**Affiliate source:** WAT Object.  
**Problem:** Greek competitor Perfectoys was cheaper and offered physical availability.  
**Decision:** **REJECT offline scarcity + deal**.

### 10. Premium laptop backpacks — REJECT

Bange/Bopai/Cardinal products from the recent affiliate shortlist were checked against Greek marketplaces. Multiple exact SKUs had 7–11 stores and/or physical pickup. Even the narrower anti-theft SKU had physical pickup evidence.  
**Decision:** **REJECT commodity/offline availability**.

### 11. Generic kids ANC / safe headphones — PAIN VALIDATED, AFFILIATE GAP NOT FOUND

The need for child-safe volume limiting and ANC/StudyMode is credible; products such as BuddyPhones Cosmos+ demonstrate a strong feature bundle. However the truly differentiated premium models checked are not currently available through a suitable Greek Linkwise merchant, while mainstream Greek kids-headphone SKUs are widely distributed or below the €50 campaign threshold.  
**Decision:** **KEEP PAIN, NO PROMOTABLE SKU YET**.

---

## Current ranking

1. **JIMI school desk + bench — Conditional near-winner**  
   Strongest combination currently found: verified demand, child-specific use, low exact Greek seller breadth, real local discount, affiliate route. Remaining blockers: exact current stock/showroom exposure and only moderate deal strength.
2. **Vipack Comfortline 201 — Strong hidden-gap benchmark**  
   Better functional gap; current deal is not strong enough.
3. **Mark Adler Junior 3.6 — Best advanced ergonomics benchmark**  
   Strong market gap, but no current Linkwise merchant.

## Final status at this snapshot

**No SKU is yet approved as an unconditional promotion winner.**

This is intentional. The campaign must not manufacture winners from weak evidence. The next useful action is to keep the validated pains (grow-with-child ergonomics and compact study-space) fixed and search the live affiliate universe for a SKU that matches the Mark Adler/Vipack feature gap **and** has a defensible Greek price advantage.
