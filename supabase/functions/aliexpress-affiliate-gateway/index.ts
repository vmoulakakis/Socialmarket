import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import CryptoJS from 'npm:crypto-js@4.2.0'

const API_URL=Deno.env.get('ALIEXPRESS_API_URL')||'https://eco.taobao.com/router/rest'
const APP_KEY=Deno.env.get('ALIEXPRESS_APP_KEY')||''
const APP_SECRET=Deno.env.get('ALIEXPRESS_APP_SECRET')||''
const TRACKING_ID=Deno.env.get('ALIEXPRESS_TRACKING_ID')||''
const APP_SIGNATURE=Deno.env.get('ALIEXPRESS_APP_SIGNATURE')||''
const SIGN_METHOD=(Deno.env.get('ALIEXPRESS_SIGN_METHOD')||'hmac').toLowerCase()

const cors={
  'access-control-allow-origin':'*',
  'access-control-allow-headers':'content-type,authorization,apikey',
  'access-control-allow-methods':'GET,POST,OPTIONS'
}
const json=(x:unknown,status=200)=>new Response(JSON.stringify(x),{
  status,headers:{...cors,'content-type':'application/json','cache-control':'no-store'}
})

function ts(){
  const d=new Date()
  const p=(n:number)=>String(n).padStart(2,'0')
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`
}

function sign(params:Record<string,string>){
  const joined=Object.keys(params).filter(k=>k!=='sign').sort().map(k=>k+params[k]).join('')
  if(SIGN_METHOD==='md5')return CryptoJS.MD5(APP_SECRET+joined+APP_SECRET).toString().toUpperCase()
  return CryptoJS.HmacMD5(joined,APP_SECRET).toString().toUpperCase()
}

async function top(method:string,business:Record<string,unknown>){
  if(!APP_KEY||!APP_SECRET)throw new Error('aliexpress_credentials_missing')
  const params:Record<string,string>={
    app_key:APP_KEY,
    format:'json',
    method,
    sign_method:SIGN_METHOD==='md5'?'md5':'hmac',
    timestamp:ts(),
    v:'2.0',
  }
  for(const [k,v] of Object.entries(business)){
    if(v!==undefined&&v!==null&&String(v)!=='')params[k]=String(v)
  }
  params.sign=sign(params)
  const body=new URLSearchParams(params)
  const r=await fetch(API_URL,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded;charset=utf-8'},body})
  const raw=await r.text()
  let data:any
  try{data=JSON.parse(raw)}catch{throw new Error(`aliexpress_non_json_${r.status}`)}
  if(!r.ok)throw new Error(`aliexpress_http_${r.status}`)
  const err=deepFind(data,'error_response')
  if(err)throw new Error(`aliexpress_api:${String(err?.sub_msg||err?.msg||err?.code||'unknown').slice(0,400)}`)
  return data
}

function deepFind(node:any,key:string):any{
  if(!node||typeof node!=='object')return null
  if(Object.prototype.hasOwnProperty.call(node,key))return node[key]
  for(const v of Object.values(node)){
    const hit=deepFind(v,key)
    if(hit!==null&&hit!==undefined)return hit
  }
  return null
}

function productArray(data:any):any[]{
  const products=deepFind(data,'products')
  if(Array.isArray(products))return products
  if(products&&Array.isArray(products.product))return products.product
  const result=deepFind(data,'result')
  if(result&&Array.isArray(result.products))return result.products
  if(result?.products&&Array.isArray(result.products.product))return result.products.product
  const single=deepFind(data,'product')
  return single&&typeof single==='object'?[single]:[]
}

function n(v:any){
  if(v===undefined||v===null||v==='')return null
  const x=Number(String(v).replace('%','').replace(',','.'))
  return Number.isFinite(x)?x:null
}

function rawProduct(x:any){
  if(!x||typeof x!=='object')return null
  const pid=String(x.product_id||x.productId||'').trim()
  const title=String(x.product_title||x.title||'').trim()
  if(!pid||!title)return null
  return {
    product_id:pid,
    product_title:title,
    product_main_image_url:x.product_main_image_url||x.image_url||x.imageUrl||null,
    product_detail_url:x.product_detail_url||x.product_url||x.productUrl||null,
    promotion_link:x.promotion_link||x.promotionLink||null,
    target_sale_price:n(x.target_sale_price??x.sale_price??x.price),
    target_sale_price_currency:x.target_sale_price_currency||x.sale_price_currency||x.currency||'EUR',
    sale_price:n(x.sale_price??x.target_sale_price??x.price),
    sale_price_currency:x.sale_price_currency||x.target_sale_price_currency||x.currency||'EUR',
    original_price:n(x.original_price??x.originalPrice),
    commission_rate:x.commission_rate??x.commissionRate??null,
    evaluate_rate:x.evaluate_rate??x.positive_feedback_rate??x.positiveFeedbackRate??null,
    lastest_volume:x.lastest_volume??x.latest_volume??x.sales??null,
    second_level_category_name:x.second_level_category_name||x.category_name||x.category||null,
    shop_id:x.shop_id??x.shopId??null,
    shop_url:x.shop_url??x.shopUrl??null,
    ship_to_days:x.ship_to_days??x.delivery_days??x.delivery??null,
    platform_product_type:x.platform_product_type??x.platformProductType??null,
    source_payload:x
  }
}

function mapped(data:any){return productArray(data).map(rawProduct).filter(Boolean)}

Deno.serve(async req=>{
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors})
  if(req.method==='GET')return json({
    ok:true,
    service:'aliexpress-affiliate-gateway',
    version:'3.0-direct',
    direct:true,
    configured:Boolean(APP_KEY&&APP_SECRET),
    tracking_configured:Boolean(TRACKING_ID),
    api_url:API_URL,
    deterministic_promotion_gate:'expected_commission_eur >= 10 only',
  })
  if(req.method!=='POST')return json({ok:false,error:'method_not_allowed'},405)
  try{
    const b=await req.json()
    const action=String(b.action||'')
    if(action==='search'||action==='hotproducts'){
      const keywords=String(b.keywords||b.query||'').trim()
      if(!keywords)throw new Error('keywords_required')
      const method=action==='hotproducts'?'aliexpress.affiliate.hotproduct.query':'aliexpress.affiliate.product.query'
      const data=await top(method,{
        app_signature:APP_SIGNATURE||undefined,
        keywords,
        page_no:Number(b.page||1),
        page_size:Math.min(50,Number(b.page_size||20)),
        sort:action==='hotproducts'?'LAST_VOLUME_DESC':String(b.sort||'LAST_VOLUME_DESC'),
        target_currency:String(b.currency||'EUR'),
        target_language:String(b.language||'EN'),
        tracking_id:TRACKING_ID||undefined,
        ship_to_country:String(b.ship_to||'GR'),
        min_sale_price:b.min_price,
        max_sale_price:b.max_price,
        delivery_days:b.delivery_days,
        fields:String(b.fields||'commission_rate,sale_price,original_price,product_title,product_id,product_main_image_url,product_detail_url,evaluate_rate,lastest_volume,second_level_category_name,shop_id')
      })
      return json({ok:true,data:{products:mapped(data),source:'aliexpress-direct',raw_meta:{method}}})
    }
    if(action==='details'){
      const ids=(Array.isArray(b.product_ids)?b.product_ids:String(b.product_ids||'').split(','))
        .map((x:any)=>String(x).trim()).filter(Boolean).slice(0,40)
      if(!ids.length)throw new Error('product_ids_required')
      const data=await top('aliexpress.affiliate.productdetail.get',{
        app_signature:APP_SIGNATURE||undefined,
        product_ids:ids.join(','),
        target_currency:String(b.currency||'EUR'),
        target_language:String(b.language||'EN'),
        tracking_id:TRACKING_ID||undefined,
        country:String(b.ship_to||'GR'),
        fields:String(b.fields||'commission_rate,sale_price,original_price,product_title,product_id,product_main_image_url,product_detail_url,evaluate_rate,lastest_volume,second_level_category_name,shop_id')
      })
      return json({ok:true,data:{products:mapped(data),source:'aliexpress-direct'}})
    }
    if(action==='generate_link'){
      const url=String(b.url||b.productUrl||'').trim()
      if(!url)throw new Error('valid_url_required')
      const data=await top('aliexpress.affiliate.link.generate',{
        app_signature:APP_SIGNATURE||undefined,
        promotion_link_type:0,
        source_values:url,
        tracking_id:TRACKING_ID||undefined
      })
      const links=deepFind(data,'promotion_links')
      const first=Array.isArray(links)?links[0]:Array.isArray(links?.promotion_link)?links.promotion_link[0]:links?.promotion_link||links
      return json({ok:true,data:{promotion_link:first?.promotion_link||first?.promotionLink||null,source:'aliexpress-direct'}})
    }
    throw new Error('action_not_allowed')
  }catch(e){
    const msg=String(e instanceof Error?e.message:e)
    return json({ok:false,error:msg},400)
  }
})
