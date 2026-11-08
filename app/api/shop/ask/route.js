import {NextResponse} from 'next/server';
import {getShopCatalog,shopBuyerRows,toPublicProducts} from '@/lib/shop-catalog';
import {searchShopCatalog,enrichTerms,inferredBudget} from '@/lib/shop-search.mjs';
import {runBuyerCrew} from '@/lib/shopper-crew.mjs';
import {aiAvailable,completeViaGateway,takeSlot} from '@/lib/shop-ai-bridge';
export const runtime='nodejs';
export const maxDuration=60;
export const dynamic='force-dynamic';
const json=(v,status=200)=>NextResponse.json(v,{status,headers:{'Cache-Control':'no-store','X-Robots-Tag':'noindex'}});
function explanation(items,query){
 if(!items.length)return 'Δεν βρήκα τεκμηριωμένη αντιστοίχιση στον διαθέσιμο κατάλογο. Δοκίμασε συγκεκριμένη κατηγορία, άλλη περιγραφή ή μεγαλύτερο όριο τιμής.';
 const cat=new Set(items.map(p=>p.category));
 return 'Βρέθηκαν '+items.length+' πραγματικές καταχωρίσεις που σχετίζονται με «'+query+'»'+(cat.size?' στις κατηγορίες '+[...cat].slice(0,3).join(', '):'')+'. Οι τιμές προέρχονται από το feed. Δεν έχουν επιβεβαιωθεί ζωντανά το απόθεμα, τα μεταφορικά και οι όροι του εμπόρου.';
}
export async function POST(req){
 let body;
 try{
   const raw=await req.text();
   if(raw.length>2200)return json({error:'request_too_large'},413);
   body=JSON.parse(raw);
 }catch{return json({error:'invalid_json'},400);}
 const question=typeof body?.message==='string'?body.message.trim():'';
 if(question.length<3||question.length>180)return json({error:'message_requires_3_to_180_characters'},400);
 const budget=body.budget==null||body.budget===''?inferredBudget(question):Number(body.budget);
 if(budget!=null&&(!Number.isFinite(budget)||budget<=0||budget>100000))return json({error:'invalid_budget'},400);
 const category=typeof body.category==='string'?body.category.slice(0,60):'Όλα';
 try{
   const {products,sourceStatus}=await getShopCatalog();
   const candidates=searchShopCatalog(products,{query:question,category,budget,perPage:30});
   const shortlist=candidates.results.slice(0,16);
   const items=toPublicProducts(shortlist.slice(0,6));
   const base={
     message:explanation(items,question),items,matched:candidates.total,sourceStatus,
     mode:'source-grounded',aiModelExecuted:false,aiReady:aiAvailable(),
     steps:[{label:'Κατανόηση ανάγκης',state:'done'},{label:'Αναζήτηση πραγματικών προϊόντων',state:'done'},
       {label:'Ελεγκτής αποδεικτικών στοιχείων',state:'limited'}],
     evidenceNotice:'Καμία πηγή δεν παρέχει επιβεβαιωμένο live stock. Η τελική τιμή και διαθεσιμότητα ελέγχονται στον έμπορο.',
   };
   if(!shortlist.length||!aiAvailable())return json(base);
   if(!(await takeSlot(req)))return json({...base,aiStatus:'quota_unavailable',
      message:base.message+' Η AI αξιολόγηση δεν ήταν διαθέσιμη, αλλά οι αντιστοιχίσεις προέρχονται από πραγματικό feed.'});
   const bilingual=question+' '+enrichTerms(question).join(' ');
   const crew=await runBuyerCrew({
     rows:shopBuyerRows(shortlist),question:bilingual,budget,complete:completeViaGateway,
   });
   if(!crew.ai_model_executed||crew.crew_status!=='AI_RESEARCH_COMPLETE_NOT_VERIFIED')
     return json({...base,aiStatus:crew.crew_status});
   const accepted=(crew.research||[]).filter(x=>crew.critic?.find(c=>c.id===x.id)?.final_verdict!=='REJECTED');
   const validatedIds=new Set(items.map(p=>p.id));
   const explanations=accepted.filter(x=>validatedIds.has(x.id)).slice(0,3).map(x=>({
     id:x.id,text:x.reason,unknowns:x.unknowns,confidence:x.confidence,
     skeptic:crew.critic?.find(c=>c.id===x.id)?.final_verdict||'NEEDS_EVIDENCE'
   }));
   const message=explanations.length
     ? 'Ο Product Fit Agent εξέτασε τις πηγές και ο Skeptic έλεγξε τις προτάσεις. Παρακάτω εμφανίζονται οι αιτιολογημένες αντιστοιχίσεις, όχι επιβεβαιωμένες αγορές.'
     :base.message;
   return json({...base,message,mode:'two-agent-research',aiModelExecuted:true,
      aiStatus:crew.crew_status,explanations,steps:[
       {label:'Κατανόηση ανάγκης',state:'done'},{label:'Πραγματικά προϊόντα',state:'done'},
       {label:'Product Fit Agent',state:'done'},{label:'Skeptic Agent',state:'done'}]});
 }catch(error){
   console.error('[shop-ask] request failed:',error?.message||'unknown');
   return json({error:'shop_assistant_unavailable',message:'Η υπηρεσία δεν είναι διαθέσιμη. Δοκίμασε ξανά.'},503);
 }
}
