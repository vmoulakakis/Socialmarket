export const MIN_COMMISSION=10;
export function safeAwinUrl(value){
 try{const u=new URL(value);return u.protocol==="https:"&&["awin1.com","www.awin1.com"].includes(u.hostname)&&!u.username&&!u.password?u.toString():null}catch{return null}
}
export function eligible(o,now=Date.now()){
 if(!o?.is_published||!o?.in_stock||o.currency!=="EUR"||!safeAwinUrl(o.tracking_url))return false;
 if(!(Number(o.price_eur)>0&&Number(o.expected_commission_eur)>=MIN_COMMISSION))return false;
 const age=now-new Date(o.verified_at).getTime();
 return Number.isFinite(age)&&age>=0&&age<=72*3600000;
}
export function selectOffers(offers,query,now=Date.now()){
 return (Array.isArray(offers)?offers:[]).filter(o=>eligible(o,now)&&
 ["tire_width","tire_profile","rim_diameter"].every(k=>Number(o[k])===Number(query[k]))&&
 (!query.season||o.season===query.season)&&
 (!query.maxPrice||Number(o.price_eur)<=Number(query.maxPrice)))
 .sort((a,b)=>{
  if(query.priority==="wet"){const rank=g=>({A:0,B:1,C:2,D:3,E:4}[g]??9);return rank(a.wet_grip_grade)-rank(b.wet_grip_grade)||Number(a.price_eur)-Number(b.price_eur);}
  return Number(a.price_eur)-Number(b.price_eur);
 }).slice(0,3);
}
