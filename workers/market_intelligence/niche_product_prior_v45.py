from __future__ import annotations

"""Greece-first niche-product query layer for Category Pain V4.5.

Broad taxonomy remains the canonical storage boundary, but research queries are
product/use-case specific. This prevents social likes/views or generic category
mentions from becoming pain evidence. Only extracted first-person/purchase-use
consumer text can survive the existing V4 skeptic gates.
"""

from urllib.parse import urlparse

import category_pain_intelligence as base
from semantic_taxonomy import fold

# Three deliberately concrete intents per high-value subcategory. They mirror the
# real-feed pain-solver families and current Greece-first commercial strategy.
NICHE_TERMS: dict[tuple[str, str], tuple[str, ...]] = {
    ('Beauty & Personal Care', 'Sun Care'): (
        'αντηλιακό προσώπου λιπαρή επιδερμίδα',
        'αντηλιακό που δεν τσούζει μάτια',
        'αντηλιακό για ιδρώτα άθληση',
    ),
    ('Beauty & Personal Care', 'Fragrance'): (
        'arabian perfume lattafa gourmand',
        'αραβικό άρωμα μεγάλη διάρκεια',
        'lattafa vanilla perfume',
    ),
    ('Fashion & Accessories', 'Footwear'): (
        'παπούτσια πεζοπορίας για ζέστη',
        'trail παπούτσια που δεν γλιστράνε',
        'ελαφριά παπούτσια πεζοπορίας',
    ),
    ('Fashion & Accessories', 'Bags & Luggage'): (
        'ανταλλακτικές ρόδες βαλίτσας',
        'packing cubes συμπίεσης βαλίτσας',
        'ζυγαριά αποσκευών ταξίδι',
    ),
    ('Home & Garden', 'Furniture'): (
        'βραχίονας οθόνης VESA γραφείο',
        'υποπόδιο γραφείου εργονομικό',
        'εργονομικό setup γραφείου μικρός χώρος',
    ),
    ('Home & Garden', 'Garden & Outdoor Living'): (
        'αυτόματο πότισμα μπαλκονιού διακοπές',
        'χρονοδιακόπτης ποτίσματος μπαλκονιού',
        'στάγδην πότισμα γλάστρες μπαλκόνι',
    ),
    ('Home & Garden', 'Home Appliances'): (
        'μπαταρία σκούπας αντικατάσταση',
        'ανταλλακτικά φίλτρα ρομπότ σκούπας',
        'καθαριστικό κλιματιστικού σπίτι',
    ),
    ('Home & Garden', 'Kitchen & Dining'): (
        'θερμική τσάντα φαγητού σχολείο',
        'δοχείο φαγητού leakproof σχολείο',
        'θερμός παγούρι σχολείο',
    ),
    ('Electronics & Technology', 'Smart Home & Gadgets'): (
        'mini UPS router ONT',
        'μετρητής κατανάλωσης ρεύματος πρίζα',
        'αισθητήρας διαρροής νερού smart home',
    ),
    ('Kids & Baby', 'School Supplies'): (
        'εκτυπωτής ετικετών bluetooth σχολείο',
        'ετικέτες οργάνωσης σχολικών',
        'θερμική τσάντα φαγητού σχολείο',
    ),
    ('Books & Education', 'Educational Materials'): (
        'σχολικά βοηθήματα γυμνασίου',
        'βοήθημα μαθηματικών γυμνασίου',
        'βοήθημα έκθεσης λυκείου',
    ),
    ('Books & Education', 'Books'): (
        'ελληνικά για ξένους βιβλίο',
        'greek language book for foreigners',
        'manga starter volume σειρά ανάγνωσης',
    ),
    ('Automotive', 'Car Parts & Accessories'): (
        'jump starter αυτοκινήτου',
        'φορητό κομπρεσέρ ελαστικών αυτοκινήτου',
        'φαρμακείο αυτοκινήτου DIN 13164',
    ),
    ('Automotive', 'Car Care'): (
        'καθαριστικό air condition αυτοκινήτου',
        'φορητό κομπρεσέρ αυτοκινήτου',
        'μετρητής πίεσης ελαστικών αυτοκινήτου',
    ),
    ('Sports & Outdoors', 'Camping & Hiking'): (
        'επαναφορτιζόμενο φανάρι camping power bank',
        'αυτοφούσκωτο στρώμα camping',
        'φορητός σταθμός ενέργειας camping',
    ),
    ('Sports & Outdoors', 'Running'): (
        'trail παπούτσια για ζέστη',
        'trail παπούτσια που γλιστράνε',
        'ελαφριά παπούτσια πεζοπορίας',
    ),
    ('Pets', 'Pet Supplies'): (
        'δίχτυ γάτας μπαλκόνι',
        'δροσιστικό στρώμα σκύλου',
        'μπουκάλι νερού σκύλου ταξίδι',
    ),
}

SOCIAL_DOMAINS = (
    'facebook.com', 'instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be',
    'reddit.com', 'x.com', 'twitter.com', 'pinterest.com', 'linkedin.com',
)
MARKETPLACE_DOMAINS = ('bestprice.gr', 'skroutz.gr')
MEGA_COMMERCE_DOMAINS = (
    'public.gr', 'kotsovolos.gr', 'e-shop.gr', 'plaisio.gr', 'e-jumbo.gr',
    'leroymerlin.gr', 'vendora.gr', 'shopflix.gr', 'notino.gr',
    'intersport.gr', 'cosmossport.gr', 'vidaxl.gr',
)

_ORIGINAL_TERMS = base.market_query_terms
_ORIGINAL_USEFUL_ROWS = base.useful_rows
_APPLIED = False


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower().removeprefix('www.')
    except Exception:
        return ''


def _is_domain(d: str, allowed: tuple[str, ...]) -> bool:
    return any(d == x or d.endswith('.' + x) for x in allowed)


def _dedup(values):
    out=[]; seen=set()
    for value in values:
        key=fold(value)
        if not key or key in seen: continue
        seen.add(key); out.append(str(value))
    return out


def market_query_terms(category: str, subcategory: str | None = None):
    original=list(_ORIGINAL_TERMS(category, subcategory))
    niche=list(NICHE_TERMS.get((str(category or ''), str(subcategory or '')), ()))
    # Concrete niche/product intent always comes first because collectors only
    # spend their largest query budget on the first aliases.
    return _dedup([*niche, *original])


def useful_rows(query, keywords, query_term, kind, limit=10):
    rows=list(_ORIGINAL_USEFUL_ROWS(query, keywords, query_term, kind, limit))

    # Demand/competition may use marketplace/merchant presence as a coverage
    # proxy, but social platforms are explicitly forbidden from inflating those
    # scores. Social evidence belongs only in the consumer pain collector.
    if kind in ('demand', 'competition'):
        qf=fold(query)
        # One targeted marketplace expansion per alias, not on every query, keeps
        # the run bounded while putting Skroutz/BestPrice ahead of generic web.
        if kind == 'demand' and ('αγορα ελλαδα' in qf or 'κριτικ' in qf):
            for site in MARKETPLACE_DOMAINS:
                rows.extend(_ORIGINAL_USEFUL_ROWS(f'site:{site} {query_term}', keywords, query_term, kind, 5))
        if kind == 'competition' and ('τιμες' in qf or 'shop' in qf):
            for site in MEGA_COMMERCE_DOMAINS[:6]:
                rows.extend(_ORIGINAL_USEFUL_ROWS(f'site:{site} {query_term}', keywords, query_term, kind, 3))

        filtered=[]
        for row in rows:
            d=_domain(str(row.get('source_url') or ''))
            if not d or _is_domain(d, SOCIAL_DOMAINS):
                continue
            meta=dict(row.get('metadata') or {})
            meta['source_role']='demand_proxy' if kind == 'demand' else 'competition_supply_proxy'
            meta['social_metrics_eligible_for_demand']=False
            meta['retrieval_version']='greece_niche_v4.5'
            row={**row, 'metadata':meta}
            filtered.append(row)
        rows=filtered

    dedup=[]; seen=set()
    for row in rows:
        key=(row.get('source_url'), row.get('title'), kind)
        if key in seen: continue
        seen.add(key); dedup.append(row)
        if len(dedup) >= limit: break
    return dedup


def apply():
    global _APPLIED
    if _APPLIED: return
    base.market_query_terms=market_query_terms
    base.useful_rows=useful_rows
    _APPLIED=True
