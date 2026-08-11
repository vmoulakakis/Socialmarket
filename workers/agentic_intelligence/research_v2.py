import re

GENERIC = {
    "review","reviews","problem","problems","issue","issues","complaints","complaint","customer","customers",
    "common","buyers","buyer","drawbacks","alternatives","competitors","what","dislike","pain","points",
    "κριτικές","κριτικες","προβλήματα","προβληματα","παράπονα","παραπονα","αγοραστές","αγοραστες",
}


def market_topic(product):
    raw = f"{product.get('category_raw','')} {product.get('product_name','')}".lower()
    if "γυαλ" in raw or "sunglass" in raw:
        return "sunglasses eyewear"
    if "φωτισ" in raw or "lamp" in raw or "light" in raw or "neon" in raw:
        return "decorative lighting home lamps"
    if "τραπέζ" in raw or "table" in raw or "sideboard" in raw:
        return "designer furniture side tables"
    if "σπίτι" in raw or "home" in raw:
        return "home decor furniture"
    cat = re.sub(r"[^\w\s-]", " ", str(product.get("category_raw") or ""), flags=re.I)
    return re.sub(r"\s+", " ", cat).strip()[:100] or "consumer product"


def discover_market_queries(products, cap):
    topics=[]
    for p in products:
        t=market_topic(p)
        if t not in topics: topics.append(t)
    queries=[]
    for t in topics:
        for q in [
            f"{t} common customer problems",
            f"{t} customer complaints drawbacks",
            f"{t} buyers dislike fit quality issues",
            f"{t} unmet needs consumer pain points",
            f"{t} alternatives competitors features",
            f"{t} reviews problems",
        ]:
            if q not in queries: queries.append(q)
            if len(queries)>=cap: return queries
    # Exact product research is secondary, after market/category pain discovery.
    for p in products:
        name=re.sub(r"\s+"," ",str(p.get("product_name") or "")).strip()[:100]
        if not name: continue
        for q in [f'"{name}" review problems', f'"{name}" alternative']:
            queries.append(q)
            if len(queries)>=cap: return queries
    return queries[:cap]


def _keywords(query):
    words=[w.lower() for w in re.findall(r"[\wα-ωάέήίόύώϊϋΐΰ-]+",query,re.I)]
    return [w for w in words if len(w)>=4 and w not in GENERIC][:8]


def relevant_searx(original, query, limit=8):
    # Ask for a wider result pool, then reject obviously unrelated search hits
    # before any page is fetched or stored as evidence.
    rows=original(query, max(limit*3,12))
    keys=_keywords(query)
    if not keys: return rows[:limit]
    scored=[]
    for r in rows:
        hay=f"{r.get('title','')} {r.get('snippet','')} {r.get('url','')}".lower()
        score=sum(1 for k in keys if k in hay)
        if score:
            scored.append((score,r))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [r for _,r in scored[:limit]]
