import hashlib, json, math, re, unicodedata
from datetime import date


def clamp(v,lo=0.0,hi=100.0):
    try:return max(lo,min(hi,float(v)))
    except:return lo


def optional_score(v):
    if v is None or v=='':return None
    try:return clamp(v)
    except:return None


def fold(v):
    s=str(v or '').lower()
    s=''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9α-ω]+',' ',s).strip()


def tokens(v):
    return {x for x in fold(v).split() if len(x)>=3 and x not in {'και','the','for','with','from','που','των','στη','στο','this','that'}}


def numeric_values(raw):
    if not raw:return []
    return [float(x.replace(',','.')) for x in re.findall(r'\d+(?:[\.,]\d+)?',str(raw))]


def parse_commission_rule(raw_pct,raw_flat,effective_price):
    """Conservative sale-commission interpretation.

    Percentage commission wins when present because flat amounts may describe a different conversion/action.
    Range programs use the LOW end for automatic eligibility so expected commission is never overstated.
    """
    pct=numeric_values(raw_pct)
    flat=numeric_values(raw_flat)
    result={
      'commission_rate_pct':None,'flat_commission_eur':None,'expected_commission_eur':0.0,
      'potential_commission_eur':0.0,'commission_rule':'unresolved','commission_confidence':0.0
    }
    if pct and effective_price and effective_price>0:
        lo,hi=min(pct),max(pct)
        result.update({
          'commission_rate_pct':lo,
          'expected_commission_eur':effective_price*lo/100.0,
          'potential_commission_eur':effective_price*hi/100.0,
          'commission_rule':'percent_exact' if len(set(pct))==1 else 'percent_range_conservative_min',
          'commission_confidence':1.0 if len(set(pct))==1 else 0.78,
        })
        return result
    if flat:
        lo,hi=min(flat),max(flat)
        result.update({
          'flat_commission_eur':lo,
          'expected_commission_eur':lo,
          'potential_commission_eur':hi,
          'commission_rule':'flat_exact' if len(set(flat))==1 else 'flat_range_conservative_min',
          'commission_confidence':1.0 if len(set(flat))==1 else 0.75,
        })
    return result


def canonical_key(p):
    gtin=fold(p.get('gtin'))
    if gtin:return 'gtin:'+re.sub(r'\s+','',gtin)
    brand=fold(p.get('brand_name')); model=fold(p.get('model_name'))
    if brand and model:
        seed='brand-model|'+brand+'|'+model
    else:
        title=fold(p.get('product_name'))
        category=fold(p.get('category_raw'))
        seed='title|'+brand+'|'+title+'|'+category
    return 'hash:'+hashlib.sha256(seed.encode()).hexdigest()[:40]


def commission_score(eur):
    """€10 is the floor; benefit rises quickly then saturates."""
    e=max(0.0,float(eur or 0))
    if e<10:return 0.0
    return clamp(20+80*(1-math.exp(-(e-10)/35.0)))


def discount_score(pct):
    return clamp(float(pct or 0)*2.2)


def lexical_relevance(product_text,rag_text):
    a=tokens(product_text); b=tokens(rag_text)
    if not a or not b:return 0.0
    inter=len(a&b)
    if not inter:return 0.0
    return clamp(18+82*(inter/max(2,min(len(a),len(b)))))


def select_pain_rag(product,clusters,limit=8):
    text=' '.join(str(product.get(k) or '') for k in ('product_name','brand_name','model_name','category_raw','description'))
    scored=[]
    pc=fold(product.get('category_raw'))
    for c in clusters:
        rag=' '.join(str(c.get(k) or '') for k in ('canonical_text','category','subcategory'))
        rel=lexical_relevance(text,rag)
        if pc and (pc in fold(c.get('category')) or fold(c.get('category')) in pc):rel=max(rel,45)
        evidence_bonus=min(15,float(c.get('source_diversity') or 0)*3)+min(10,float(c.get('evidence_count') or 0))
        score=rel*.72+clamp(c.get('pain_severity') or 0)*.12+clamp(c.get('demand_score') or 0)*.08+evidence_bonus*.08
        if score>=18:scored.append((score,c))
    scored.sort(key=lambda x:x[0],reverse=True)
    return [{**c,'retrieval_score':round(s,2)} for s,c in scored[:limit]]


def seasonal_curve(theme,today=None):
    today=today or date.today()
    def d(v):
        try:return date.fromisoformat(str(v)) if v else None
        except:return None
    start,peak,end=d(theme.get('active_from')),d(theme.get('peak_date')),d(theme.get('active_to'))
    if not start or not peak or not end:return 50.0
    if today<start or today>end:return 0.0
    if today<=peak:
        span=max(1,(peak-start).days); pos=max(0,(today-start).days)
        return clamp(40+60*pos/span)
    span=max(1,(end-peak).days); pos=max(0,(today-peak).days)
    return clamp(100-70*pos/span)


def select_theme_rag(product,themes,limit=5):
    text=' '.join(str(product.get(k) or '') for k in ('product_name','brand_name','model_name','category_raw','description'))
    scored=[]
    for t in themes:
        rel=lexical_relevance(text,' '.join(str(t.get(k) or '') for k in ('name','semantic_brief')))
        season=seasonal_curve(t)
        score=rel*.68+season*.32
        if score>=15:scored.append((score,season,t))
    scored.sort(key=lambda x:x[0],reverse=True)
    return [{**t,'retrieval_score':round(s,2),'seasonal_curve_score':round(season,2)} for s,season,t in scored[:limit]]


def evidence_metrics(selected_pains,merchant):
    pains=selected_pains or []
    demand_values=[optional_score(x.get('demand_score')) for x in pains if x.get('demand_score') is not None]
    merchant_demand=optional_score(merchant.get('demand_score'))
    if merchant_demand is not None:demand_values.append(merchant_demand)
    demand=max(demand_values) if demand_values else None

    comps=[optional_score(x.get('competition_score')) for x in pains if x.get('competition_score') is not None]
    comps=[x for x in comps if x is not None]
    merchant_comp=optional_score(merchant.get('competition_score'))
    competition=(sum(comps)/len(comps)) if comps else merchant_comp

    pain_conf=sum(float(x.get('confidence') or 0) for x in pains)/len(pains) if pains else 0
    merchant_conf=float(merchant.get('confidence') or 0)
    confidence=clamp(((pain_conf+merchant_conf)/2.0)*100 if pains else merchant_conf*100)
    return {
      'greek_demand_score':round(demand,2) if demand is not None else None,
      'competition_score':round(competition,2) if competition is not None else None,
      'evidence_confidence':round(confidence,2),
      'competition_missing':competition is None,
      'demand_missing':demand is None,
    }


def final_opportunity_score(*,pain_gap_fit,merchant_opportunity,greek_demand,competition,seasonal_theme,merchant_trust,expected_commission,discount,evidence_confidence):
    values={
      'pain_gap_fit_score':optional_score(pain_gap_fit),
      'merchant_opportunity_score':optional_score(merchant_opportunity),
      'greek_demand_score':optional_score(greek_demand),
      'competition_score':optional_score(competition),
      'seasonal_theme_score':optional_score(seasonal_theme),
      'merchant_trust_score':optional_score(merchant_trust),
      'commission_score':commission_score(expected_commission),
      'discount_score':discount_score(discount),
      'product_evidence_confidence':optional_score(evidence_confidence),
    }
    positive=lambda key:(values[key] if values[key] is not None else 0.0)
    inverse_comp=(100-values['competition_score']) if values['competition_score'] is not None else 0.0
    score=(
      positive('pain_gap_fit_score')*.25+
      positive('merchant_opportunity_score')*.20+
      positive('greek_demand_score')*.15+
      values['commission_score']*.12+
      inverse_comp*.10+
      positive('seasonal_theme_score')*.08+
      positive('merchant_trust_score')*.05+
      values['discount_score']*.03+
      positive('product_evidence_confidence')*.02
    )
    missing=[k for k,v in values.items() if v is None]
    values['missing_components']=missing
    values['competition_inverse_bonus_withheld']=values['competition_score'] is None
    return round(clamp(score),2),values


def compact_product_for_ai(p):
    return {k:p.get(k) for k in (
      'source_record_hash','external_product_id','product_name','brand_name','model_name','category_raw','description',
      'price','full_price','discount_pct','expected_commission_eur','commission_rule','times_bought','merchant_name'
    )}
