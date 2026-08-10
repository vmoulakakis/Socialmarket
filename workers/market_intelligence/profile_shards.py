import gzip,glob,json,collections

def main(pattern='shards/*.jsonl.gz'):
    total=price_150=with_tracking=with_image=valid_20_plus=travel_excluded=eligible=0
    categories=collections.Counter();eligible_categories=collections.Counter();travel_categories=collections.Counter();price_bands=collections.Counter();discount_bands=collections.Counter();runway_bands=collections.Counter();exclusion_reasons=collections.Counter()
    for path in glob.glob(pattern):
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                x=json.loads(line);total+=1
                price=x.get('price') or 0;tracking=bool(x.get('tracking_url'));image=bool(x.get('image_url') or x.get('thumb_url'));discount=x.get('discount_pct') or 0;days=x.get('validity_days_remaining')
                category=x.get('category_raw') or 'Uncategorized';categories[category]+=1
                if price>=150:price_150+=1
                if tracking:with_tracking+=1
                if image:with_image+=1
                if days is not None and days>20:valid_20_plus+=1
                if x.get('travel_related'):
                    travel_excluded+=1;travel_categories[category]+=1
                if x.get('hard_gate_pass'):
                    eligible+=1;eligible_categories[category]+=1
                for reason in (x.get('eligibility_reason') or {}).get('reasons',[]):exclusion_reasons[reason]+=1
                price_bands['150-299' if 150<=price<300 else '300-599' if 300<=price<600 else '600-999' if 600<=price<1000 else '1000+' if price>=1000 else '<150']+=1
                discount_bands['40%+' if discount>=40 else '30-39%' if discount>=30 else '15-29%' if discount>=15 else '<15%']+=1
                runway_bands['missing/expired' if days is None or days<=0 else '1-20d' if days<=20 else '21-30d' if days<=30 else '31-60d' if days<=60 else '61-90d' if days<=90 else '91d+']+=1
    result={
      'total':total,'price_150_plus':price_150,'valid_to_more_than_20_days':valid_20_plus,'with_tracking_url':with_tracking,'with_image':with_image,
      'travel_excluded':travel_excluded,'eligible_after_feed_gates':eligible,'exclusion_reasons':exclusion_reasons.most_common(),
      'top_categories_all':categories.most_common(50),'top_categories_eligible':eligible_categories.most_common(50),'top_travel_categories_excluded':travel_categories.most_common(30),
      'price_bands':dict(price_bands),'discount_bands':dict(discount_bands),'validity_runway_bands':dict(runway_bands)
    }
    print(json.dumps(result,ensure_ascii=False,indent=2))
    open('feed-profile.json','w',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
