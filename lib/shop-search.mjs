import {normalize} from './shopper-agent.mjs';
const STOP=new Set('θελω θελουμε χρειαζομαι για μου ενα μια εναν στο στην με που και να εχει το την τη κατι πολυ απο εως ευρω ευρώ αποστολη αγορα θελω να δω i want a the for with of best product'.split(' '));
const DICT=[
 ['φωτισ','lamp lighting chandelier pendant light ceiling led'],
 ['λαμπ','lamp light lighting bulb'],
 ['πολυελ','chandelier pendant lighting'],
 ['αυτοκιν','car automotive vehicle auto obd'],
 ['διαγνωσ','diagnostic scanner obd ecu repair'],
 ['σκαν','scanner diagnostic automotive'],
 ['καναπ','sofa couch seater living room'],
 ['σαλον','living room sofa home'],
 ['κηπ','garden outdoor planting'],
 ['εργαλ','tool tools repair maintenance'],
 ['καθαρισ','clean cleaning cleaner vacuum'],
 ['σκουπ','vacuum cleaner robot'],
 ['θερμαν','heating heater thermostat'],
 ['ρομποτ','robot robotic automatic'],
 ['σπιτ','home house decor indoor smart'],
 ['φωτογραφ','camera photography lens'],
 ['στολισ','decor decoration home'],
 ['διακοσμ','decor interior home'],
 ['μετρ','measurement meter measuring tester'],
 ['μετρη','meter measurement analyzer'],
 ['μπαταρ','battery power charger'],
 ['παιχν','toy toys gaming'],
 ['ζω','pet cat dog'],
 ['σκυλ','pet dog'],
 ['γατ','pet cat'],
 ['κινητ','phone mobile smartphone'],
 ['ακουστ','headphone audio wireless'],
 ['φορτιστ','charger charging usb'],
 ['ηλεκτρικ','electric electronics'],
 ['ποδηλα','bicycle bike cycling'],
 ['ασυρματ','wireless wifi bluetooth'],
 ['οροφ','ceiling pendant lighting'],
 ['δωματ','room indoor home'],
 ['μπανιο','bathroom washroom'],
 ['κουζιν','kitchen cooking dining'],
 ['κατοικ','home house'],
];
export function tokenizeQuery(q){
 return normalize(q).split(/\s+/).filter(x=>x.length>=3&&!STOP.has(x)).slice(0,15);
}
export function enrichTerms(q){
 const source=tokenizeQuery(q),terms=new Set(source);
 for(const term of source) for(const [prefix,english] of DICT)
   if(term.startsWith(prefix))english.split(' ').forEach(e=>terms.add(e));
 return [...terms];
}
export function inferredBudget(q){
 const m=normalize(q).match(/(?:μεχρι|εως|max|under|budget)\s*(\d{1,5})(?:\s*(?:ευρω|euro|eur))?/);
 if(m){const n=Number(m[1]);return n>0&&n<100000?n:null}
 return null;
}
export function productRelevance(p,query){
 const terms=enrichTerms(query);
 const title=normalize(p.title),category=normalize(p.sourceCategory||p.category),vendor=normalize(p.merchant);
 const explicit=tokenizeQuery(query);
 let intentBonus=0;
 if(explicit.some(t=>t.startsWith('οροφ')) && title.includes('ceiling')) intentBonus+=24;
 if(explicit.some(t=>t.startsWith('διαγνωσ')) && title.includes('diagnostic')) intentBonus+=18;
 const matched=terms.reduce((sum,t)=>{
   if(t.length<3)return sum;
   const base=t.length>=7?t.slice(0,6):t;
   return sum+(title.includes(base)?7:0)+(category.includes(base)?4:0)+(vendor.includes(base)?0.7:0);
 },0);
 return matched+intentBonus;
}
const FRESH={recent:3,aging:2,unknown:0,stale:-5};
export function searchShopCatalog(products,{query='',category='Όλα',budget=null,sort='relevance',page=1,perPage=24}={}){
 const budgetVal=budget==null||budget===''?inferredBudget(query):Number(budget);
 const cap=Number.isFinite(Number(budgetVal))&&Number(budgetVal)>0?Number(budgetVal):null;
 const termCount=tokenizeQuery(query).length;
 const filtered=products.filter(p=>(category==='Όλα'||p.category===category) &&
   (cap==null||p.price<=cap) && (!termCount||productRelevance(p,query)>0));
 const withScores=filtered.map(p=>({p,score:productRelevance(p,query)+FRESH[p.freshness]}));
 withScores.sort((a,b)=>{
   if(sort==='price-asc')return a.p.price-b.p.price||b.score-a.score;
   if(sort==='price-desc')return b.p.price-a.p.price||b.score-a.score;
   if(sort==='fresh')return FRESH[b.p.freshness]-FRESH[a.p.freshness]||b.score-a.score;
   return b.score-a.score||a.p.price-b.p.price;
 });
 const current=Math.max(1,Math.min(50,Number(page)||1));
 const length=Math.min(48,Math.max(1,Number(perPage)||24));
 const start=(current-1)*length;
 return {results:withScores.slice(start,start+length).map(x=>x.p),total:withScores.length,
   page:current,pageSize:length,hasMore:start+length<withScores.length,
   extractedBudget:cap,terms:enrichTerms(query).slice(0,24)};
}
