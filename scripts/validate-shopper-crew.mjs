import assert from 'node:assert/strict';
import {evidencePacket,validateResearch,validateSkeptic,runBuyerCrew} from '../lib/shopper-crew.mjs';
const now=new Date('2026-11-06T10:00:00Z');
const tracking='https://go.linkwi.se/z/23-0/CD104/?lnkurl=https%3A%2F%2Fshop.gr%2Fitem';
const row={
 source_product_id:'item-1',product_name:'Γωνιακός καναπές',program_name:'Shop',category_raw:'Καθιστικό',
 price_eur:480,calculated_commission_eur:48,tracking_url:tracking,image_url:'https://shop.gr/item.jpg',
 in_stock:null,is_active:true,last_seen_at:'2026-11-06T09:00:00Z',valid_to:null
};
const packet=evidencePacket({rows:[row],question:'θέλω γωνιακό καναπέ',budget:500,now});
assert.equal(packet.products.length,1);
assert.equal(packet.products[0].id,'item-1');
assert.equal(JSON.stringify(packet.products).includes('go.linkwi.se'),false);
assert.equal(packet.result.verified.length,0);
assert.equal(packet.result.candidates[0].tracking_url,tracking);
const researchResponse={provider:'mock',model:'offline-fixture',
 content:JSON.stringify({ranked:[{id:'item-1',reason:'Καταχωρισμένος γωνιακός καναπές εντός προϋπολογισμού',unknowns:['stock','freshness'],confidence:0.5}]})};
const skepticResponse={provider:'mock',model:'offline-fixture',
 content:JSON.stringify({reviews:[{id:'item-1',verdict:'VALIDATED',reason:'Χρειάζεται ανεξάρτητη επαλήθευση stock και audit'}]})};
const ranked=validateResearch(researchResponse,packet.products);
assert.equal(ranked.length,1);
assert.equal(ranked[0].id,'item-1');
assert.throws(()=>validateResearch({content:JSON.stringify({ranked:[{id:'another-item',reason:'fake',unknowns:[]}]})},packet.products),/mismatch/);
assert.throws(()=>validateResearch({content:'not json'},packet.products),/invalid_provider_json/);
const reviewed=validateSkeptic(skepticResponse,ranked);
assert.equal(reviewed[0].final_verdict,'NEEDS_EVIDENCE','model cannot promote evidence state');
let called=0;
const complete=async arg=>{
 called++;
 assert.equal(JSON.stringify(arg.messages).includes('go.linkwi.se'),false,'tracking links never sent to LLM');
 assert.equal(arg.maxTokens,500);
 assert.equal(arg.accessToken,'mock-admin-token');
 return called===1?researchResponse:skepticResponse;
};
const result=await runBuyerCrew({rows:[row],question:'θέλω γωνιακό καναπέ',budget:500,now,complete,accessToken:'mock-admin-token'});
assert.equal(called,2);
assert.equal(result.crew_status,'AI_RESEARCH_COMPLETE_NOT_VERIFIED');
assert.equal(result.publication_approved,false);
assert.equal(result.research.length,1);
assert.equal(result.critic[0].final_verdict,'NEEDS_EVIDENCE');
assert.equal(result.verified.length,0);
const failures=await runBuyerCrew({rows:[row],question:'γωνιακός καναπές',now,complete:async()=>{throw new Error('provider failure')},accessToken:'mock'});
assert.equal(failures.crew_status,'SAFE_HOLD_MODEL_OR_AUDIT_UNAVAILABLE');
assert.equal(failures.research.length,0);
const tamper=await runBuyerCrew({rows:[row],question:'γωνιακός καναπές',now,complete:async()=>({content:JSON.stringify({ranked:[{id:'unexpected',reason:'x',unknowns:[]}]})}),accessToken:'mock'});
assert.equal(tamper.crew_status,'SAFE_HOLD_MODEL_OR_AUDIT_UNAVAILABLE');
assert.equal(tamper.publication_approved,false);
const noModel=await runBuyerCrew({rows:[row],question:'γωνιακός καναπές',now,complete:null});
assert.equal(noModel.ai_model_executed,false);
assert.equal(noModel.crew_status,'MODEL_NOT_CONFIGURED');
const noMatch=await runBuyerCrew({rows:[row],question:'ηλεκτρική σκούπα',now,complete:async()=>{throw Error('should not call')}});
assert.equal(noMatch.crew_status,'NO_RESEARCH_CANDIDATES');
console.log('Buyer Crew: deterministic evidence, model JSON contracts, skeptic veto, zero URL leakage and safe-hold fixtures passed.');
