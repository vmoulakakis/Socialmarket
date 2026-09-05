import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

// Marketplace 200 compatibility gateway.
// Secrets remain in the proven travelai Supabase runtime; this function never
// receives, stores, logs, or exposes ALIEXPRESS_APP_SECRET.
const UPSTREAM='https://bgvgstpoypqbjnemqcqp.supabase.co/functions/v1/aliexpress-affiliate'
const json=(x:unknown,status=200)=>new Response(JSON.stringify(x),{status,headers:{'content-type':'application/json','cache-control':'no-store','access-control-allow-origin':'*'}})

async function upstream(body:Record<string,unknown>){
  const r=await fetch(UPSTREAM,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)})
  const raw=await r.text();let data:any
  try{data=JSON.parse(raw)}catch{throw new Error(`upstream_non_json_${r.status}`)}
  if(!r.ok)throw new Error(`upstream_${r.status}:${String(data?.error||'request_failed').slice(0,240)}`)
  return data
}

function rawProduct(x:any){
  if(!x||typeof x!=='object')return null
  const pid=String(x.productId||'').trim(),title=String(x.title||'').trim()
  if(!pid||!title)return null
  return {
    product_id:pid,
    product_title:title,
    product_main_image_url:x.imageUrl||null,
    product_detail_url:x.productUrl||null,
    promotion_link:x.promotionLink||null,
    target_sale_price:x.price??null,
    target_sale_price_currency:x.currency||'EUR',
    sale_price:x.price??null,
    sale_price_currency:x.currency||'EUR',
    original_price:x.originalPrice??null,
    commission_rate:x.commissionRate??null,
    evaluate_rate:x.positiveFeedbackRate??null,
    lastest_volume:x.sales??null,
    second_level_category_name:x.category??null,
    shop_id:x.shopId??null,
    shop_url:x.shopUrl??null,
    ship_to_days:x.delivery??null,
    platform_product_type:x.platformProductType??null,
  }
}

function mapped(products:any[]){return products.map(rawProduct).filter(Boolean)}

Deno.serve(async req=>{
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:{'access-control-allow-origin':'*','access-control-allow-headers':'content-type,authorization'}})
  if(req.method==='GET')return json({
    ok:true,service:'aliexpress-affiliate-gateway',version:'2.0-proxy',configured:true,tracking_configured:true,
    credential_location:'server-side upstream runtime',upstream:'travelai/aliexpress-affiliate',
    evidence_fields:['product_id','product_title','product_main_image_url','product_detail_url','promotion_link','target_sale_price','commission_rate','evaluate_rate','lastest_volume','second_level_category_name','shop_id','shop_url','ship_to_days']
  })
  if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
  try{
    const b=await req.json(),action=String(b.action||'')
    if(action==='search'||action==='hotproducts'){
      const payload:any={
        action:'search',query:String(b.keywords||b.query||'').trim(),shipToCountry:String(b.ship_to||'GR'),currency:String(b.currency||'EUR'),
        page:Number(b.page||1),pageSize:Math.min(50,Number(b.page_size||20)),sort:action==='hotproducts'?'LAST_VOLUME_DESC':String(b.sort||'LAST_VOLUME_DESC')
      }
      if(!payload.query)throw new Error('keywords_required')
      if(b.min_price!==undefined)payload.minPrice=Number(b.min_price)
      if(b.max_price!==undefined)payload.maxPrice=Number(b.max_price)
      if(b.delivery_days!==undefined)payload.deliveryDays=Number(b.delivery_days)
      const data=await upstream(payload)
      return json({ok:true,data:{products:mapped(Array.isArray(data?.products)?data.products:[]),source:'travelai-aliexpress-live'}})
    }
    if(action==='details'){
      const ids=(Array.isArray(b.product_ids)?b.product_ids:String(b.product_ids||'').split(',')).map((x:any)=>String(x).trim()).filter(Boolean).slice(0,40)
      const products=[]
      for(const id of ids){
        try{const data=await upstream({action:'product_detail',productId:id});const p=rawProduct(data?.product);if(p)products.push(p)}catch{/* detail refresh is best-effort; discovery data remains authoritative */}
      }
      return json({ok:true,data:{products,source:'travelai-aliexpress-live'}})
    }
    if(action==='generate_link'){
      const productUrl=String(b.url||b.productUrl||'').trim();if(!productUrl)throw new Error('valid_url_required')
      const data=await upstream({action:'generate_link',productUrl})
      const promotion=String(data?.promotionLink||'')
      if(!/^https:\/\/s\.click\.aliexpress\.com\//i.test(promotion))throw new Error('upstream_invalid_promotion_link')
      return json({ok:true,data:{promotion_link:promotion,product_id:data?.productId||null,source:'travelai-aliexpress-live'}})
    }
    throw new Error('action_not_allowed')
  }catch(e){return json({ok:false,error:String(e instanceof Error?e.message:e)},500)}
})
