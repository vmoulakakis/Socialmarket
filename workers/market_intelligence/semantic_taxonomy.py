from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


def fold(text: str | None) -> str:
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", s).strip()


TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "Fashion & Accessories": {
        "Apparel": ("clothing", "clothes", "apparel", "fashion", "ρουχα", "ενδυ", "μπλουζ", "πουκαμισ", "παντελον", "φορεμ", "ζακετ", "μπουφαν"),
        "Footwear": ("shoe", "shoes", "footwear", "sneaker", "boot", "sandals", "παπουτ", "μποτ", "σανδαλ"),
        "Bags & Luggage": ("bag", "bags", "handbag", "backpack", "luggage", "suitcase", "travel bag", "baggage", "τσαντ", "σακιδ", "βαλιτσ", "αποσκευ"),
        "Jewelry & Watches": ("jewelry", "jewellery", "jewel", "watch", "watches", "κοσμη", "ρολογ"),
        "Eyewear & Accessories": ("eyewear", "sunglass", "glasses", "belt", "wallet", "γυαλ", "ζων", "πορτοφολ"),
    },
    "Beauty & Personal Care": {
        "Skincare": ("skincare", "skin care", "serum", "face cream", "moistur", "περιποιηση προσωπου", "κρεμα προσωπου", "ορος προσωπου"),
        "Sun Care": ("sunscreen", "sun care", "spf", "αντηλια", "ηλιοπροστα"),
        "Makeup": ("makeup", "make-up", "cosmetic", "foundation", "mascara", "lipstick", "μακιγιαζ", "καλλυν"),
        "Hair Care": ("hair care", "shampoo", "conditioner", "hair color", "μαλλι", "σαμπουαν"),
        "Fragrance": ("perfume", "fragrance", "cologne", "αρωμα"),
        "Personal Care": ("personal care", "body care", "deodorant", "oral care", "περιποιηση σωματος", "στοματικ"),
    },
    "Health & Wellness": {
        "Supplements": ("supplement", "vitamin", "protein", "creatine", "συμπληρω", "βιταμιν", "πρωτειν"),
        "Pharmacy & OTC": ("pharmacy", "otc", "parapharmacy", "φαρμακ", "παραφαρμακ"),
        "Wellness & Recovery": ("wellness", "massage", "recovery", "orthopedic", "ορθοπεδ", "μασαζ", "αποκατασταση"),
    },
    "Electronics & Technology": {
        "Computers & Laptops": ("computer", "laptop", "notebook computer", "desktop pc", "υπολογισ", "λαπτοπ"),
        "Phones & Accessories": ("smartphone", "mobile phone", "phone case", "phone charger", "κινητ", "τηλεφων", "φορτιστ"),
        "TV & Audio": ("television", "smart tv", "speaker", "headphone", "audio", "τηλεορα", "ηχει", "ακουστικ"),
        "Gaming": ("gaming", "game console", "playstation", "xbox", "nintendo", "gamepad"),
        "Smart Home & Gadgets": ("smart home", "gadget", "wearable", "smartwatch", "security camera", "καμερα", "gadget"),
    },
    "Home & Garden": {
        "Furniture": ("furniture", "sofa", "chair", "dining table", "bed", "επιπλ", "καναπ", "καρεκλ", "κρεβατ"),
        "Home Decor": ("home decor", "decoration", "canvas art", "wall art", "διακοσμ", "πινακ", "καμβα"),
        "Kitchen & Dining": ("kitchen", "cookware", "dining", "kitchenware", "κουζιν", "μαγειρ"),
        "Bathroom": ("bathroom", "bath accessory", "bath towel", "μπανιο", "πετσετ"),
        "Garden & Outdoor Living": ("garden", "outdoor furniture", "patio", "bbq", "κηπ", "βεραντ", "ψησταρ"),
        "Home Appliances": ("home appliance", "appliance", "vacuum", "coffee machine", "air fryer", "συσκευ", "σκουπα", "καφετιερ"),
        "Bedding & Textiles": ("bedding", "mattress", "pillow", "linen", "στρωμα", "μαξιλαρ", "σεντον"),
    },
    "Sports & Outdoors": {
        "Fitness": ("fitness", "gym equipment", "training equipment", "weights", "yoga", "γυμνασ", "βαρη"),
        "Running": ("running", "runner", "trail running", "τρεξιμ"),
        "Cycling": ("cycling", "bicycle", "bike", "ποδηλα"),
        "Camping & Hiking": ("camping", "hiking", "tent", "outdoor gear", "καμπιν", "πεζοπορ"),
        "Sports Equipment": ("sports equipment", "football equipment", "basketball", "tennis", "αθλητικ", "μπαλα", "τενις"),
    },
    "Kids & Baby": {
        "Baby Care": ("baby care", "diaper", "baby feeding", "stroller", "βρεφ", "πανα", "καροτσ"),
        "Kids Clothing": ("kids clothing", "children clothing", "παιδικα ρουχα", "παιδικη ενδυση"),
        "Toys & Games": ("toy", "toys", "board game", "lego", "παιχνιδ"),
        "School Supplies": ("school supplies", "stationery", "school bag", "pencil", "τετραδι", "σχολικα", "γραφικη υλη", "κασετιν"),
    },
    "Books & Education": {
        "Books": ("bookstore", "books", "publisher", "publishing house", "βιβλιοπωλ", "βιβλια", "εκδοσεις"),
        "Educational Materials": ("educational material", "learning material", "study guide", "school book", "εκπαιδευ", "μαθησιακ", "βοηθημα"),
        "Courses & Training": ("online course", "training course", "seminar", "μαθημα", "σεμιναρ", "καταρτιση"),
    },
    "Food & Drink": {
        "Grocery": ("grocery", "food store", "supermarket", "τροφ", "παντοπωλ"),
        "Coffee & Tea": ("coffee", "tea", "espresso", "καφε", "τσα"),
        "Wine & Beverages": ("wine", "beer", "beverage", "drink store", "κρασι", "ποτο", "ροφημ"),
        "Specialty Food": ("organic food", "delicatessen", "gourmet food", "βιολογικ", "delicatessen"),
    },
    "Travel": {
        "Flights": ("flight", "flights", "airline", "air ticket", "airfare", "πτηση", "αεροπορ", "εισιτηρια αεροπορ"),
        "Hotels & Accommodation": ("hotel", "accommodation", "resort", "ξενοδοχ", "διαμον"),
        "Ferries & Sea Travel": ("ferry", "ferries", "ferry ticket", "sea travel", "ship ticket", "ακτοπλο", "πλοιο", "πλοια", "εισιτηρια πλοι"),
        "Travel Packages & Activities": ("travel package", "tour package", "travel activity", "excursion", "πακετο διακοπων", "εκδρομ"),
        "Car Rental": ("car rental", "rent a car", "rental car", "ενοικιαση αυτοκινητου"),
    },
    "Automotive": {
        "Car Parts & Accessories": ("car part", "auto part", "car accessories", "ανταλλακτικ", "αξεσουαρ αυτοκινητου"),
        "Tyres & Wheels": ("tyre", "tire", "car wheel", "ελαστικ", "ζαντ"),
        "Motorcycle": ("motorcycle", "moto gear", "scooter", "μοτοσυκ", "μηχαν"),
        "Car Care": ("car care", "detailing", "motor oil", "λιπαντικ", "περιποιηση αυτοκινητου"),
    },
    "Pets": {
        "Pet Food": ("pet food", "dog food", "cat food", "τροφη σκυλου", "τροφη γατας", "ζωοτροφ"),
        "Pet Supplies": ("pet supplies", "pet accessories", "cat litter", "λουρι", "αξεσουαρ κατοικιδ"),
        "Pet Health": ("pet health", "veterinary", "flea treatment", "κτηνιατρ", "αντιπαρασιτ"),
    },
    "Services & Digital": {
        "Software & SaaS": ("software", "saas", "app subscription", "λογισμικ"),
        "Cybersecurity & VPN": ("vpn", "virtual private network", "cybersecurity", "antivirus", "online privacy", "identity protection", "scam protection", "phishing protection", "ασφαλεια διαδικτυου", "κυβερνοασφαλ", "προστασια ταυτοτητας"),
        "Hosting & Domains": ("web hosting", "hosting", "domain registration", "server hosting", "φιλοξενια ιστοσελιδ"),
        "Finance & Insurance": ("insurance", "banking", "loan service", "ασφαλ", "τραπεζ", "δανει"),
        "Telecom & Utilities": ("telecom", "internet provider", "energy provider", "mobile network", "τηλεπικοινων", "ενεργεια"),
    },
}

CATEGORY_ALIASES = {"fashion":"Fashion & Accessories","fashion / footwear":"Fashion & Accessories","beauty":"Beauty & Personal Care","health":"Health & Wellness","electronics":"Electronics & Technology","electronics / technology":"Electronics & Technology","home & garden":"Home & Garden","sports & outdoors":"Sports & Outdoors","sports / outdoor":"Sports & Outdoors","kids & baby":"Kids & Baby","food & drink":"Food & Drink","travel":"Travel","automotive":"Automotive","pets":"Pets","services":"Services & Digital"}
NAVIGATION_PATTERNS=(r"\bskip to\b",r"\bjump to\b",r"\bgo to (main )?content\b",r"\bsign[ -]?up\b",r"\blog[ -]?in\b",r"\bregister\b",r"\bmy account\b",r"\blost password\b",r"\bcart\b",r"\bcheckout\b",r"\bcookies?\b",r"\bprivacy\b",r"\bterms( of use)?\b",r"\bcompany\b",r"\babout us\b",r"\bcontact\b",r"\bhelp\b",r"μεταβαση στο",r"παραλειψη",r"συνδεση",r"εγγραφ",r"λογαριασ",r"καλαθι",r"κωδικ.*προωθητικ",r"πολιτικη απορρητου",r"οροι χρησης",r"ποιοι ειμαστε",r"η εταιρεια",r"βοηθεια",r"πληροφορι",r"παρακολουθηση παραγγελιας",r"εξελιξη παραγγελιας",r"καταστηματα?",r"κατηγοριες?",r"προιοντα?$")
PROMO_PATTERNS=(r"\bsale\b",r"\boffers?\b",r"\bdiscount\b",r"\bcoupon\b",r"\bpromo\b",r"%",r"hot\d+",r"εκπτω",r"προσφορ",r"κουπον",r"δωρεαν αποστολ",r"δωροεπιταγ")
THEME_PATTERNS=(r"back[ -]?to[ -]?school",r"black friday",r"cyber monday",r"christmas",r"xmas",r"valentine",r"mother.?s day",r"father.?s day",r"summer( favourites?| sales?)?",r"winter sale",r"school season",r"χριστουγεν",r"παναγια",r"αγιου βαλεντιν",r"καλοκαιρ",r"επιστροφη στο σχολειο")
SERVICE_PATTERNS=(r"payment",r"shipping",r"delivery",r"returns?",r"refund",r"warranty",r"track(ing)? order",r"πληρωμ",r"αποστολ",r"παραδοση",r"επιστροφ",r"εγγυησ",r"παραγγελι")
LANGUAGE_LABELS={"english","german","greek","francais","french","deutsch","ελληνικα","αγγλικα","γερμανικα"}
GREEK_LOCATIONS={"αθηνα","θεσσαλονικη","πατρα","ηρακλειο","λαρισα","βολος","ιωαννινα","χαλκιδα","πειραιας","ροδος","κρητη","κυπρος","greece","athens","thessaloniki"}


def _matches(patterns: Iterable[str], value: str) -> bool:return any(re.search(p,value,re.I) for p in patterns)
def _keyword_score(text:str,keywords:Iterable[str])->int:
    low=fold(text);score=0
    for kw in keywords:
        k=fold(kw)
        if not k:continue
        if " " in k:
            if k in low:score+=4
        elif len(k)>=5 and re.search(rf"(?<!\w){re.escape(k)}\w*",low):score+=1
    return score

def classify_label(label:str|None)->dict:
    raw=str(label or '').strip();low=fold(raw)
    if not raw or len(low)<2:return {'label':raw,'role':'noise','confidence':1.0,'reason':'empty_or_too_short'}
    if low in LANGUAGE_LABELS:return {'label':raw,'role':'language','confidence':.99,'reason':'language_switch'}
    if low in GREEK_LOCATIONS:return {'label':raw,'role':'location','confidence':.99,'reason':'geo_label'}
    if _matches(NAVIGATION_PATTERNS,low):return {'label':raw,'role':'navigation','confidence':.99,'reason':'navigation_or_account_ui'}
    if _matches(SERVICE_PATTERNS,low):return {'label':raw,'role':'service_policy','confidence':.95,'reason':'service_or_policy'}
    if _matches(PROMO_PATTERNS,low):return {'label':raw,'role':'promotion','confidence':.98,'reason':'campaign_or_offer_label'}
    if _matches(THEME_PATTERNS,low):return {'label':raw,'role':'theme','confidence':.98,'reason':'seasonal_or_campaign_theme'}
    scored=[]
    for category,subs in TAXONOMY.items():
        for sub,kws in subs.items():
            s=_keyword_score(low,(*kws,sub,category))
            if s:scored.append((s,category,sub))
    if scored:
        scored.sort(reverse=True);s,cat,sub=scored[0]
        return {'label':raw,'role':'product_taxonomy','category':cat,'subcategory':sub,'confidence':min(.96,.58+s*.07),'reason':'canonical_keyword_match'}
    words=re.findall(r"[A-Za-zΑ-ΩΆΈΉΊΌΎΏα-ωάέήίόύώϊϋΐΰ0-9]+",raw);alpha=[w for w in words if any(ch.isalpha() for ch in w)]
    if 1<=len(alpha)<=4 and len(raw)<=45:
        upperish=sum(1 for w in alpha if len(w)>1 and(w.isupper() or w[:1].isupper()))
        if upperish>=max(1,len(alpha)-1):return {'label':raw,'role':'brand_or_collection','confidence':.72,'reason':'brand_like_without_product_semantics'}
    if re.search(r"\d{1,2}:\d{2}:\d{2}|^\d{1,2}[ηης]?\b",low):return {'label':raw,'role':'noise','confidence':.95,'reason':'timestamp_or_counter'}
    if '�' in raw or re.search(r"[ÎÃ]{1,2}[A-Za-zΑ-Ωα-ω]",raw):return {'label':raw,'role':'noise','confidence':.9,'reason':'encoding_noise'}
    return {'label':raw,'role':'unknown','confidence':.45,'reason':'no_commercial_taxonomy_evidence'}

@dataclass(frozen=True)
class TaxonomyResolution:
    category:str;subcategory:str|None;confidence:float;source:str;label_audit:tuple[dict,...];evidence:tuple[dict,...]=()
    def as_dict(self)->dict:return {'category':self.category,'subcategory':self.subcategory,'confidence':self.confidence,'source':self.source,'label_audit':list(self.label_audit),'evidence':list(self.evidence)}

def _score_identity_surface(merchant_name:str,title:str,description:str)->dict[tuple[str,str],float]:
    scores={}
    for text,weight in ((merchant_name,7.0),(title,8.0),(description,6.0)):
        if not text:continue
        for category,subs in TAXONOMY.items():
            for sub,kws in subs.items():
                raw=_keyword_score(text,(*kws,sub,category))
                if raw:scores[(category,sub)]=scores.get((category,sub),0)+raw*weight
    return scores

def resolve_merchant_taxonomy(merchant_name:str,site_title:str,site_description:str,anchors:Iterable[str],existing_category:str|None=None,existing_subcategory:str|None=None)->TaxonomyResolution:
    audits=tuple(classify_label(x) for x in list(anchors)[:140]);identity_scores=_score_identity_surface(merchant_name,site_title,site_description);scores=dict(identity_scores);evidence=[{'kind':'identity_surface','category':c,'subcategory':s,'score':round(v,2)} for(c,s),v in scores.items()]
    votes={};seen=set()
    for a in audits:
        if a.get('role')!='product_taxonomy':continue
        lk=fold(a.get('label'))
        if lk in seen:continue
        seen.add(lk);key=(a['category'],a['subcategory']);votes[key]=votes.get(key,0)+min(.85,float(a.get('confidence') or 0))*2.0
    for key,v in votes.items():scores[key]=scores.get(key,0)+min(v,5.0);evidence.append({'kind':'anchor_vote','category':key[0],'subcategory':key[1],'score':round(min(v,5.0),2)})
    prior=CATEGORY_ALIASES.get(fold(existing_category)) or next((c for c in TAXONOMY if fold(c)==fold(existing_category)),None)
    if prior:
        for key in list(scores):
            if key[0]==prior:scores[key]+=1.5
    old=classify_label(existing_subcategory)
    if old.get('role')=='product_taxonomy':key=(old['category'],old['subcategory']);scores[key]=scores.get(key,0)+1.0
    if not scores:return TaxonomyResolution('Other',None,.20,'merchant_identity_unresolved_v4.3',audits,tuple(evidence))
    ranked=sorted(scores.items(),key=lambda kv:kv[1],reverse=True);(top_cat,top_sub),best=ranked[0];identity_top=identity_scores.get((top_cat,top_sub),0)
    category_totals={c:sum(v for(c2,_),v in scores.items() if c2==c) for c in TAXONOMY};cat_rank=sorted(category_totals.items(),key=lambda kv:kv[1],reverse=True);category_margin=cat_rank[0][1]-(cat_rank[1][1] if len(cat_rank)>1 else 0)
    if identity_top<6 and category_margin<8:return TaxonomyResolution('Other',None,.30,'insufficient_identity_surface_v4.3',audits,tuple(evidence))
    confidence=min(.97,.56+min(identity_top,36)*.008+min(max(category_margin,0),30)*.006)
    same=sorted([(v,s) for(c,s),v in scores.items() if c==top_cat],reverse=True);sub_second=same[1][0] if len(same)>1 else 0;sub_margin=best-sub_second
    if identity_top<10 or sub_margin<4:return TaxonomyResolution(top_cat,None,min(confidence,.78),'merchant_category_only_v4.3',audits,tuple(evidence))
    return TaxonomyResolution(top_cat,top_sub,confidence,'merchant_identity_weighted_v4.3',audits,tuple(evidence))

def resolve_taxonomy(merchant_name:str,corpus:str,anchors:Iterable[str],existing_category:str|None=None,existing_subcategory:str|None=None)->TaxonomyResolution:
    compact=' '.join(str(corpus or '').split()[:120]);return resolve_merchant_taxonomy(merchant_name,compact,'',anchors,existing_category,existing_subcategory)

def is_valid_taxonomy_label(label:str|None)->bool:return classify_label(label).get('role')=='product_taxonomy'
