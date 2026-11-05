import {readFile} from "node:fs/promises";
import {fileURLToPath} from "node:url";

const KNOWN=new Set(["joined","pending","notjoined","rejected","suspended"]);
export function normalizeMembership(value){
 const s=String(value??"").trim().toLowerCase().replace(/[ _-]/g,"");
 return KNOWN.has(s)?s:"unknown";
}
export function validateProgramme(p){
 if(!Number.isInteger(p?.id)||p.id<=0)throw Error("invalid advertiser id");
 if(typeof p.name!=="string"||!p.name.trim())throw Error("missing advertiser name");
 if(!KNOWN.has(p.status))throw Error("unknown status for "+p.id);
 if(p.reasonGreek && [...p.reasonGreek].length>150)throw Error("application note exceeds 150 Unicode characters: "+p.id);
 if(p.applicationState==="submitted" && p.status!=="pending" && p.status!=="joined" && p.status!=="rejected"){
   throw Error("submitted requires provider application evidence: "+p.id);
 }
 return true;
}
export function applicationGate(p){
 validateProgramme(p);
 if(p.status==="pending")return {allowed:false,reason:"already_pending"};
 if(p.status==="joined")return {allowed:false,reason:"already_joined"};
 if(p.status==="rejected")return {allowed:false,reason:"rejected_review_required"};
 if(p.status==="suspended")return {allowed:false,reason:"suspended"};
 if(p.applicationState==="submitted")return {allowed:false,reason:"already_submitted"};
 if(!p.priority)return {allowed:false,reason:"not_priority"};
 if(!p.reasonGreek)return {allowed:false,reason:"missing_tailored_note"};
 if(!p.publisherSiteVerified)return {allowed:false,reason:"publisher_site_unverified"};
 if(!p.termsReviewed)return {allowed:false,reason:"advertiser_terms_unreviewed"};
 return {allowed:true,reason:"ready_for_authorized_browser_join"};
}
export function trackingGate(p){
 validateProgramme(p);
 if(p.status!=="joined")return {allowed:false,reason:"not_joined"};
 if(!p.commissionConfirmed)return {allowed:false,reason:"commission_not_confirmed"};
 if(!p.trackingVerified)return {allowed:false,reason:"tracking_not_verified"};
 return {allowed:true,reason:"reviewed_joined_and_tracking_verified"};
}
export function rankQueue(data){
 if(data.publisherId!==3060863)throw Error("publisher mismatch");
 const ids=new Set();
 for(const p of data.programmes){
  validateProgramme(p);
  if(ids.has(p.id))throw Error("duplicate programme: "+p.id);
  ids.add(p.id);
 }
 return [...data.programmes].filter(p=>p.priority!=null).sort((a,b)=>a.priority-b.priority).map(p=>({
  id:p.id,name:p.name,relationship:p.status,epcEUR:p.epcEUR,
  applicationState:p.applicationState,reasonGreek:p.reasonGreek,gate:applicationGate(p)
 }));
}
export function summary(data){
 const counts={joined:0,pending:0,notjoined:0,rejected:0,suspended:0};
 for(const p of data.programmes){validateProgramme(p);counts[p.status]++;}
 return {publisherId:data.publisherId,source:data.source,checkedAt:data.checkedAt,counts,priority:rankQueue(data)};
}
async function main(){
 const url=new URL("../data/awin/application-queue.json",import.meta.url);
 const data=JSON.parse(await readFile(url,"utf8"));
 process.stdout.write(JSON.stringify(summary(data),null,2)+"\n");
}
if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]) await main();
