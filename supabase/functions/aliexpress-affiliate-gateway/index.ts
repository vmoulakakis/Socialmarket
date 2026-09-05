import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

const APP_KEY = Deno.env.get('ALIEXPRESS_APP_KEY') || ''
const APP_SECRET = Deno.env.get('ALIEXPRESS_APP_SECRET') || ''
const TRACKING_ID = Deno.env.get('ALIEXPRESS_TRACKING_ID') || ''
const API_URL = 'https://eco.taobao.com/router/rest'
const PRODUCT_FIELDS = [
  'product_id','product_title','product_main_image_url','product_small_image_urls','product_video_url',
  'product_detail_url','promotion_link','sale_price','sale_price_currency','target_sale_price','target_sale_price_currency',
  'original_price','original_price_currency','commission_rate','hot_product_commission_rate','relevant_market_commission_rate',
  'evaluate_rate','lastest_volume','first_level_category_id','first_level_category_name','second_level_category_id',
  'second_level_category_name','shop_id','shop_url','ship_to_days','platform_product_type','discount'
].join(',')

const json = (x: unknown, status = 200) => new Response(JSON.stringify(x), { status, headers: { 'content-type': 'application/json', 'access-control-allow-origin': '*' } })
const enc = new TextEncoder()

function hex(bytes: ArrayBuffer) { return [...new Uint8Array(bytes)].map(b => b.toString(16).padStart(2, '0')).join('').toUpperCase() }
function timestampGMT8() { const d = new Date(Date.now() + 8 * 3600_000); return d.toISOString().slice(0,19).replace('T',' ') }
async function sign(params: Record<string,string>) {
  const canonical = Object.keys(params).sort().map(k => k + params[k]).join('')
  const key = await crypto.subtle.importKey('raw', enc.encode(APP_SECRET), { name:'HMAC', hash:'SHA-256' }, false, ['sign'])
  return hex(await crypto.subtle.sign('HMAC', key, enc.encode(canonical)))
}
async function call(method:string, extra:Record<string,string>) {
  if (!APP_KEY || !APP_SECRET) throw new Error('aliexpress_credentials_not_configured')
  const params:Record<string,string> = { app_key:APP_KEY, method, format:'json', sign_method:'hmac-sha256', timestamp:timestampGMT8(), v:'2.0', ...extra }
  params.sign = await sign(params)
  const body = new URLSearchParams(params)
  const r = await fetch(API_URL, { method:'POST', headers:{'content-type':'application/x-www-form-urlencoded;charset=utf-8'}, body })
  const text = await r.text(); let data:any; try { data=JSON.parse(text) } catch { data={raw:text} }
  if (!r.ok) throw new Error(`aliexpress_http_${r.status}`)
  return data
}

Deno.serve(async req => {
  if (req.method === 'OPTIONS') return new Response(null,{status:204,headers:{'access-control-allow-origin':'*','access-control-allow-headers':'content-type,authorization'}})
  if (req.method === 'GET') return json({ok:true,service:'aliexpress-affiliate-gateway',configured:Boolean(APP_KEY&&APP_SECRET),tracking_configured:Boolean(TRACKING_ID),evidence_fields:PRODUCT_FIELDS.split(',')})
  if (req.method !== 'POST') return json({error:'method_not_allowed'},405)
  try {
    const b = await req.json(); const action=String(b.action||'')
    const tracking=String(b.tracking_id||TRACKING_ID)
    if (action==='search') {
      const x:any={ fields:PRODUCT_FIELDS, target_currency:String(b.currency||'EUR'), target_language:String(b.language||'EN'), ship_to_country:String(b.ship_to||'GR'), page_no:String(b.page||1), page_size:String(Math.min(50,Number(b.page_size||20))), sort:String(b.sort||'LAST_VOLUME_DESC') }
      if(b.keywords)x.keywords=String(b.keywords); if(b.min_price)x.min_sale_price=String(b.min_price); if(b.max_price)x.max_sale_price=String(b.max_price); if(b.delivery_days)x.delivery_days=String(b.delivery_days); if(tracking)x.tracking_id=tracking
      return json({ok:true,data:await call('aliexpress.affiliate.product.query',x)})
    }
    if (action==='hotproducts') {
      const x:any={ fields:PRODUCT_FIELDS, target_currency:String(b.currency||'EUR'), target_language:String(b.language||'EN'), ship_to_country:String(b.ship_to||'GR'), page_no:String(b.page||1), page_size:String(Math.min(50,Number(b.page_size||20))) }; if(b.keywords)x.keywords=String(b.keywords); if(b.min_price)x.min_sale_price=String(b.min_price); if(b.delivery_days)x.delivery_days=String(b.delivery_days); if(tracking)x.tracking_id=tracking
      return json({ok:true,data:await call('aliexpress.affiliate.hotproduct.query',x)})
    }
    if (action==='details') {
      const ids=(Array.isArray(b.product_ids)?b.product_ids:String(b.product_ids||'').split(',')).map((x:any)=>String(x).trim()).filter(Boolean).slice(0,50)
      if(!ids.length)throw new Error('product_ids_required')
      const x:any={fields:PRODUCT_FIELDS,product_ids:ids.join(','),target_currency:String(b.currency||'EUR'),target_language:String(b.language||'EN'),country:String(b.ship_to||'GR')};if(tracking)x.tracking_id=tracking
      return json({ok:true,data:await call('aliexpress.affiliate.productdetail.get',x)})
    }
    if (action==='generate_link') {
      if(!tracking) throw new Error('tracking_id_not_configured'); const source=String(b.url||''); if(!/^https?:\/\//i.test(source)) throw new Error('valid_url_required')
      return json({ok:true,data:await call('aliexpress.affiliate.link.generate',{source_values:source,tracking_id:tracking,promotion_link_type:String(b.promotion_link_type||0)})})
    }
    throw new Error('action_not_allowed')
  } catch(e) { return json({ok:false,error:String(e instanceof Error?e.message:e)},500) }
})
