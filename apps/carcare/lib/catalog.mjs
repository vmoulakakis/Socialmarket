// CarCare GR: pure, testable feed parsing and evidence-first matching.
const fold=v=>String(v??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const decode=v=>String(v??"").replace(/&amp;/gi,"&").replace(/&gt;/gi,">").replace(/&lt;/gi,"<").replace(/&#39;/gi,"'");
export const PROBLEMS={
visibility:{label:"Ορατότητα & παρμπρίζ",keywords:["υαλοκαθαρισ","wiper","παρμπριζ","windshield","καθαριστικ τζαμ","glass cleaner"],category:["υαλοκαθαρισ","παρμπριζ","αυτοκιν"]},
lighting:{label:"Φώτα & λάμπες",keywords:["λαμπ","h7","h4","h11","led","φωτισ","headlight","xenon"],category:["λαμπ","φωτισ","ηλεκτρικ"]},
cleaning:{label:"Καθαρισμός & περιποίηση",keywords:["καθαρισ","πλυσ","σφουγγ","γυαλισ","κερι","wax","polish","microfiber","μικροιν","σαμπουαν","detail"],category:["καθαρισμ","περιποιησ"]},
electrical:{label:"Ηλεκτρικά & μικροεπισκευές",keywords:["διακοπτ","ρελε","αισθητ","switch","sensor","παραθυρ","μοτερ","βαλβιδ"],category:["ηλεκτρικ","ανταλλακτικ"]},
gadgets:{label:"Gadgets & πρακτικότητα",keywords:["φορτιστ","charger","holder","βαση","camera","καμερα","usb","bluetooth","gps","organizer"],category:["gadgets","αξεσουαρ","ηλεκτρονικ"]},
maintenance:{label:"Αναλώσιμα & συντήρηση",keywords:["φιλτρ","filter","μπουζ","spark","λιπαντ","λαδι","oil","ανταλλακτικ","φρενο","τακακ","brake"],category:["ανταλλακτικ","αναλωσιμ"]}
};
export function parsePrice(value){
 if(typeof value==="number")return Number.isFinite(value)?value:NaN;
 let s=String(value??"").trim().replace(/[^0-9,.\-]/g,"");
 if(!s)return NaN;
 const comma=s.lastIndexOf(","),dot=s.lastIndexOf(".");
 if(comma>=0&&dot>=0)s=comma>dot?s.replace(/\./g,"").replace(",","."):s.replace(/,/g,"");
 else if(comma>=0)s=s.replace(",",".");
 return Number(s);
}
export function validTracking(value){
 try{const u=new URL(String(value||""));return u.protocol==="https:"&&!u.username&&!u.password&&(u.hostname==="linkwi.se"||u.hostname.endsWith(".linkwi.se")||u.hostname==="linkwise.gr"||u.hostname.endsWith(".linkwise.gr"))?u.href:null}catch{return null}
}
function imageUrl(value){try{const u=new URL(String(value||""));return u.protocol==="https:"&&!u.username&&!u.password?u.href:null}catch{return null}}
function dateValid(from,to,now){
 if(from){const d=new Date(from);if(!Number.isFinite(+d)||+d>+now)return false}
 if(to){const s=String(to);const d=new Date(/^\d{4}-\d{2}-\d{2}$/.test(s)?s+"T23:59:59Z":s);if(!Number.isFinite(+d)||+d<+now)return false}
 return true
}
function available(v){const s=fold(v).trim();return v!==false&&v!==0&&!["0","false","no","n","out of stock","out_of_stock","unavailable","sold out","εξαντληθηκε","μη διαθεσιμο"].includes(s)}
const isCarCategory=c=>/αυτοκιν|αυτοκινητ|automotive|car accessories|vehicle|gadgets αυτοκιν|ανταλλακτικ|υαλοκαθαρισ|αναλωσιμα αυτοκιν/i.test(c);
export function rowsOf(doc){return Array.isArray(doc)?doc:["products","items","data","product","offers"].map(k=>doc?.[k]).find(Array.isArray)||[]}
export function normalizeFeed(doc,{now=new Date()}={}){
 const seen=new Set(),items=[];
 for(const [i,p] of rowsOf(doc).entries()){
  const category=decode(p.category||""),title=decode(p.product_name||p.model_name||p.title||"").trim();
  if(!isCarCategory(category)||!title)continue;
  const price=parsePrice(p.price??p.price_eur),link=validTracking(p.tracking_url);
  if(!Number.isFinite(price)||price<=0||!link||String(p.currency||"EUR").toUpperCase()!=="EUR"||!available(p.in_stock)||!available(p.availability)||!dateValid(p.valid_from,p.valid_to,now))continue;
  const id=String(p.lw_product_id||p.product_id||i);
  if(seen.has(id))continue;seen.add(id);
  const image_url=imageUrl(p.image_url)||imageUrl(p.thumb_url);
  items.push({id,title,brand:decode(p.brand_name||""),category,merchant:decode(p.program_name||""),price,full_price:parsePrice(p.full_price),tracking_url:link,image_url,description:decode(String(p.description||"").replace(/<[^>]*>/g," ")).slice(0,480),valid_to:p.valid_to||null});
 }
 return items;
}
export function scoreMatch(p,key){
 const spec=PROBLEMS[key];if(!spec)return 0;
 const title=fold(p.title),category=fold(p.category),desc=fold(p.description);
 const strong=spec.keywords.reduce((score,word)=>{const w=fold(word);return score+(title.includes(w)?6:0)+(category.includes(w)?2:0)+(desc.includes(w)?1:0)},0);
 if(strong===0)return 0;
 return strong+spec.category.reduce((n,w)=>n+(category.includes(fold(w))?1:0),0);
}
export function selectProducts(products,{problem="visibility",q="",maxPrice=null,limit=36}={}){
 const term=fold(q).trim();
 return products.filter(p=>(!maxPrice||p.price<=maxPrice)&&(!term||fold(p.title+" "+p.brand+" "+p.category).includes(term))).map(p=>({...p,match_score:scoreMatch(p,problem)})).filter(p=>p.match_score>0).sort((a,b)=>b.match_score-a.match_score||a.price-b.price).slice(0,Math.max(1,Math.min(60,limit)));
}
