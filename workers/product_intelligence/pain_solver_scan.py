from __future__ import annotations

import html, json, math, os, re, sqlite3, unicodedata
from collections import Counter
from pathlib import Path

STAGE_DB = Path(os.getenv('PRODUCT_STAGE_DB', 'product-stage.sqlite3'))
OUT = Path(os.getenv('PRODUCT_PAIN_SOLVER_PATH', 'product-pain-solver-sample.json'))
PROFILE = Path(os.getenv('PRODUCT_PAIN_SOLVER_PROFILE_PATH', 'product-pain-solver-profile.json'))

FAMILIES = [
    dict(id='school_lunch', label='School thermal lunch / leakproof food transport', base=96, timing=100, demo=94,
         terms=['lunch bag','lunch box','bento','leakproof','thermal lunch','insulated lunch','φαγητοδοχει','δοχειο φαγητου','θερμικη τσαντα','θερμομονωτικη τσαντα']),
    dict(id='sunscreen', label='Sunscreen by use case / skin type', base=93, timing=88, demo=92,
         terms=['sunscreen','sun screen','spf 30','spf 50','spf30','spf50','αντηλιακ','αντηλιακο']),
    dict(id='packing', label='Packing compression / luggage weight control', base=91, timing=84, demo=95,
         terms=['packing cube','compression bag','vacuum bag travel','luggage scale','baggage scale','ζυγαρια αποσκευ','οργανωτ βαλιτσ','σακουλα συμπιεσ']),
    dict(id='label_printer', label='Bluetooth / thermal label printer', base=92, timing=96, demo=98,
         terms=['label printer','thermal label','bluetooth label','dymo','brother p-touch','ptouch','εκτυπωτ ετικετ','θερμικ εκτυπωτ ετικετ']),
    dict(id='hiking_footwear', label='Hot-weather hiking / trail footwear', base=88, timing=82, demo=88,
         terms=['hiking','trail running','trail shoe','trekking','πεζοπορ','ορειβατικ','trail']),
    dict(id='desk_ergonomics', label='Desk ergonomics / monitor arm / footrest', base=89, timing=94, demo=96,
         terms=['monitor arm','monitor stand','vesa arm','footrest','ergonomic foot','βραχιον οθον','βαση οθον','υποποδιο','εργονομικ γραφει']),
    dict(id='mini_ups', label='Mini UPS for router / ONT continuity', base=96, timing=86, demo=99,
         terms=['mini ups','router ups','dc ups','ups router','ups modem','ups 12v','ups 9v','ups 5v','τροφοδοτικο ups router']),
    dict(id='energy_monitor', label='Smart electricity / energy monitoring', base=94, timing=86, demo=99,
         terms=['energy monitor','power meter','watt meter','wattmeter','smart plug power','smart meter plug','μετρητ ενεργειας','μετρητ καταναλωσης','μετρητης ρευματος']),
    dict(id='school_study', label='School study aids / learning bundles', base=86, timing=100, demo=82,
         terms=['school aid','study guide','workbook','σχολικ βοηθημ','βοηθημα μαθηματ','βοηθημα φυσικ','βοηθημα χημει','βοηθημα εκθεσ']),
    dict(id='greek_learning', label='Greek-learning material for non-native speakers', base=88, timing=76, demo=84,
         terms=['learn greek','learning greek','greek language','greek for foreigners','ελληνικα για ξενους','μαθαινω ελληνικα']),
    dict(id='ac_maintenance', label='Air-conditioner cleaning / maintenance accessories', base=95, timing=94, demo=98,
         terms=['air conditioner cleaner','air condition cleaner','ac cleaner','coil cleaner','κλιματιστικ καθαρισ','καθαριστικ κλιματισ','καθαρισμο κλιματισ']),
    dict(id='vacuum_replacement', label='Cordless vacuum replacement battery / filter', base=97, timing=80, demo=96,
         terms=['vacuum battery','vacuum filter','replacement battery vacuum','replacement filter vacuum','μπαταρι σκουπ','φιλτρ σκουπ','ανταλλακτικ σκουπ']),
    dict(id='robot_vacuum_consumables', label='Robot-vacuum consumables by exact model', base=96, timing=80, demo=96,
         terms=['robot vacuum filter','robot vacuum brush','roomba filter','roomba brush','ρομποτ σκουπ φιλτρ','ρομποτ σκουπ βουρτσ','ανταλλακτικ ρομποτ σκουπ']),
    dict(id='car_safety', label='Car safety / compliance kit', base=95, timing=80, demo=90,
         terms=['din 13164','car first aid','first aid car','car extinguisher','warning triangle','φαρμακειο αυτοκινητ','πυροσβεστηρ αυτοκινητ','τριγωνο ασφαλειας','γιλεκο ασφαλειας']),
    dict(id='irrigation', label='Balcony / garden watering automation', base=95, timing=92, demo=98,
         terms=['drip irrigation','irrigation timer','watering timer','self watering','automatic watering','ποτισμα','ποτιστικ','αυτοματο ποτισ','αυτοποτιζ','σταγδην']),
    dict(id='arabian_fragrance', label='Arabian fragrance discovery', base=84, timing=76, demo=96,
         terms=['lattafa','afnan','armaf','maison alhambra','al haramain','rasasi']),
    dict(id='car_emergency', label='Jump starter / tire inflator emergency tool', base=97, timing=82, demo=100,
         terms=['jump starter','battery booster','tire inflator','tyre inflator','portable compressor car','εκκινητ μπαταρι','booster μπαταρι','κομπρεσερ αυτοκινητ','φουσκωτ ελαστικ']),
    dict(id='water_leak', label='Water-leak / flood sensor', base=96, timing=84, demo=100,
         terms=['water leak sensor','leak detector','flood sensor','water sensor','αισθητηρ διαρρο','ανιχνευτ διαρρο','αισθητηρας νερου']),
    dict(id='fridge_alarm', label='Fridge/freezer temperature alarm', base=91, timing=91, demo=98,
         terms=['fridge alarm','freezer alarm','fridge thermometer','freezer thermometer','θερμομετρο ψυγειου','θερμομετρο καταψυξ','συναγερμο ψυγειου']),
    dict(id='insect_screen', label='DIY insect / mosquito screen', base=86, timing=91, demo=95,
         terms=['mosquito screen','insect screen','window screen','magnetic screen','σιτα παραθυρ','σιτα πορτ','μαγνητικ σιτα']),
    dict(id='pet_balcony_safety', label='Cat / pet balcony safety net', base=90, timing=88, demo=94,
         terms=['cat safety net','cat balcony net','pet safety net','διχτυ γατ','διχτυ προστασιας γατ','διχτυ μπαλκονι γατ']),
    dict(id='luggage_repair', label='Luggage wheel / handle repair', base=91, timing=89, demo=100,
         terms=['luggage wheel replacement','suitcase wheel replacement','replacement luggage wheel','luggage repair wheel','ροδα βαλιτσ','ροδες βαλιτσ','ανταλλακτικ βαλιτσ']),
    dict(id='ev_accessory', label='EV Type-2 cable / organization accessory', base=84, timing=78, demo=88,
         terms=['type 2 charging cable','type2 charging cable','ev charging cable','ev cable holder','type 2 holder','καλωδιο φορτισης ev','καλωδιο type 2','θηκη καλωδιου type 2']),
    dict(id='humidity_control', label='Humidity / dehumidification control', base=93, timing=54, demo=92,
         terms=['dehumidifier','humidity monitor','hygrometer','αφυγραντ','υγρασιομετρο','μετρητ υγρασιας']),
    dict(id='power_backup', label='Portable power station / backup power', base=90, timing=78, demo=98,
         terms=['portable power station','power station','solar generator','φορητ σταθμ ενεργ','σταθμ ενεργειας']),
    dict(id='pet_cooling', label='Pet cooling / travel hydration', base=88, timing=91, demo=96,
         terms=['pet cooling mat','dog cooling mat','pet water bottle','dog travel bottle','δροσιστικ στρωμα κατοικιδ','μπουκαλι νερου σκυλ']),
]

BLOCK_TERMS = ['cbd','thc','vape','ηλεκτρονικο τσιγαρο','τσιγαρ','nicotine','νικοτιν','sex toy','vibrator','dildo','weapon','gun','knife','μαχαιρι','supplement','συμπληρωμα διατροφης','slimming','weight loss pill','φαρμακο','prescription']
SOLUTION_WORDS = ['sensor','detector','monitor','alarm','protector','protective','replacement','repair','kit','starter','inflator','filter','battery','organizer','holder','cleaner','timer','automatic','smart','ups','scale','thermal','insulated','αισθητηρ','ανιχνευτ','συναγερ','προστατ','ανταλλακ','επισκευ','κιτ','φιλτρ','μπαταρι','οργανωτ','καθαριστ','χρονοδιακοπτ','αυτοματ','εξυπν','θερμικ']
COLOR_SIZE_WORDS = {'black','white','red','blue','green','pink','grey','gray','gold','silver','brown','beige','μαυρο','μαυρη','λευκο','λευκη','κοκκινο','μπλε','πρασινο','ροζ','γκρι','χρυσο','ασημι','καφε'}

def fold(v):
    s=html.unescape(str(v or '')).lower()
    s=''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))
    s=re.sub(r'[^a-z0-9α-ω]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def hit_count(text, terms): return sum(1 for t in terms if fold(t) in text)
def clamp(x,a=0,b=100): return max(a,min(b,x))
def commission_score(eur): return clamp(28 + 36*math.log10(max(1,max(0,float(eur or 0)))))

def title_signature(name, brand=''):
    toks=[]
    for x in fold(name).split():
        if x in COLOR_SIZE_WORDS or re.fullmatch(r'\d+(?:x\d+)*',x) or len(x)<=1: continue
        toks.append(x)
    return fold(brand)+'|'+' '.join(toks[:12])

def evaluate(p, pre):
    name=fold(p.get('product_name')); cat=fold(p.get('category_raw')); desc=fold(p.get('description')); all_text=f'{name} {cat} {desc}'
    if any(fold(x) in all_text for x in BLOCK_TERMS): return []
    merchant=p.get('merchant_context') or {}
    trust=float(merchant.get('trust_score') or 0); whitespace=float(merchant.get('solution_whitespace_score') or 0); demand=float(merchant.get('demand_score') or 0)
    comp=float(merchant.get('competition_score') if merchant.get('competition_score') is not None else 50); commission=float(p.get('expected_commission_eur') or 0)
    quality=clamp(trust*.55 + whitespace*.25 + (100-comp)*.10 + min(100,demand)*.10); solution_bonus=clamp(hit_count(all_text,SOLUTION_WORDS)*8,0,24)
    out=[]
    for fam in FAMILIES:
        hn=hit_count(name,fam['terms']); hc=hit_count(cat,fam['terms']); hd=hit_count(desc,fam['terms'])
        if not (hn or hc or hd): continue
        relevance=clamp(fam['base']*.58 + hn*18 + hc*10 + hd*5 + solution_bonus)
        score=clamp(relevance*.34 + trust*.14 + whitespace*.12 + commission_score(commission)*.12 + (100-comp)*.08 + demand*.06 + fam['demo']*.07 + fam['timing']*.07)
        if hn==0 and hd==0: score-=8
        if trust<45: score-=6
        out.append({'pain_family':fam['id'],'pain_label':fam['label'],'pain_relevance_score':round(relevance,2),'pain_solver_score':round(clamp(score),2),'current_timing_score':fam['timing'],'content_demo_score':fam['demo'],'name_hits':hn,'category_hits':hc,'description_hits':hd,'quality_score':round(quality,2),'merchant_trust':trust,'merchant_solution_whitespace':whitespace,'merchant_demand':demand,'merchant_competition':comp,'commercial_preliminary_score':round(float(pre or 0),3),'commission_score':round(commission_score(commission),2)})
    return out

def main():
    if not STAGE_DB.exists(): raise SystemExit(f'missing stage db: {STAGE_DB}')
    db=sqlite3.connect(STAGE_DB); candidates=[]; family_counts=Counter(); scanned=0
    for payload, pre in db.execute('select payload, preliminary_score from candidates'):
        scanned+=1; p=json.loads(payload)
        for s in evaluate(p,pre):
            family_counts[s['pain_family']]+=1
            candidates.append({**s,'external_product_id':p.get('external_product_id'),'canonical_key':p.get('canonical_key'),'product_name':p.get('product_name'),'model_name':p.get('model_name'),'brand_name':p.get('brand_name'),'merchant_name':p.get('merchant_name'),'category_raw':html.unescape(str(p.get('category_raw') or '')),'effective_price':p.get('price'),'full_price':p.get('full_price'),'discount_pct':p.get('discount_pct'),'expected_commission_eur':p.get('expected_commission_eur'),'commission_rule':p.get('commission_rule'),'tracking_url':p.get('tracking_url'),'target_url':p.get('target_url'),'image_url':p.get('image_url') or p.get('thumb_url'),'thumb_url':p.get('thumb_url'),'extra_images':(p.get('extra_images') or [])[:5],'availability':p.get('availability'),'in_stock':p.get('in_stock'),'times_bought':p.get('times_bought'),'gtin':p.get('gtin'),'mpn':p.get('mpn'),'price_integrity':p.get('price_integrity'),'title_signature':title_signature(p.get('product_name'),p.get('brand_name'))})
    db.close(); candidates.sort(key=lambda x:(x['pain_solver_score'],x['pain_relevance_score'],x['merchant_trust'],x['expected_commission_eur'] or 0),reverse=True)
    selected=[]; fam_used=Counter(); merchant_used=Counter(); sig_used=Counter(); canonical=set()
    for x in candidates:
        if x['canonical_key'] in canonical or fam_used[x['pain_family']]>=12 or merchant_used[x['merchant_name']]>=10 or sig_used[x['title_signature']]>=1: continue
        canonical.add(x['canonical_key']); fam_used[x['pain_family']]+=1; merchant_used[x['merchant_name']]+=1; sig_used[x['title_signature']]+=1; selected.append(x)
        if len(selected)>=250: break
    OUT.write_text(json.dumps(selected,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    profile={'stage_candidate_rows_scanned':scanned,'matched_product_family_rows':len(candidates),'selected_diverse_products':len(selected),'families_with_matches':len(fam_used),'raw_match_counts_by_family':dict(family_counts.most_common()),'selected_counts_by_family':dict(fam_used.most_common()),'selected_counts_by_merchant':dict(merchant_used.most_common()),'policy':{'source':'existing Linkwise stage candidates from the 3.84GB feed','prerequisite_gates':'merchant resolved; trust floor; in stock not false; tracking URL; image; EUR price; price integrity; expected commission >= EUR10','excel_role':'pain-family priors derived from DB-fused Top-20 plus adjacent explicit problem-solving families','score':'34 pain relevance + 14 trust + 12 whitespace + 12 commission + 8 inverse competition + 6 merchant demand + 7 demo + 7 timing','persistence':'read-only diagnostic; no Supabase product persistence','claims':'discovery score only; product function/specs/stock must be verified before publishing'}}
    PROFILE.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'pain_solver_scan':profile},ensure_ascii=False),flush=True)

if __name__=='__main__': main()
