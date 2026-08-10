import gzip,glob,json,collections

def main(pattern='shards/*.jsonl.gz'):
    total=active_price=with_tracking=with_image=eligible_basic=0
    categories=collections.Counter();price_bands=collections.Counter();discount_bands=collections.Counter()
    for path in glob.glob(pattern):
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                x=json.loads(line);total+=1
                price=x.get('price') or 0;instock=x.get('in_stock');tracking=bool(x.get('tracking_url'));image=bool(x.get('image_url') or x.get('thumb_url'));discount=x.get('discount_percent') or 0
                categories[x.get('category_raw') or 'Uncategorized']+=1
                if price>=150:active_price+=1
                if tracking:with_tracking+=1
                if image:with_image+=1
                if price>=150 and instock is not False and tracking and image:eligible_basic+=1
                price_bands['150-299' if 150<=price<300 else '300-599' if 300<=price<600 else '600-999' if 600<=price<1000 else '1000+' if price>=1000 else '<150']+=1
                discount_bands['40%+' if discount>=40 else '30-39%' if discount>=30 else '15-29%' if discount>=15 else '<15%']+=1
    result={'total':total,'price_150_plus':active_price,'with_tracking_url':with_tracking,'with_image':with_image,'basic_gate_candidates':eligible_basic,'top_categories':categories.most_common(50),'price_bands':dict(price_bands),'discount_bands':dict(discount_bands)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    open('feed-profile.json','w',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
