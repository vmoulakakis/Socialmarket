import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {applicationGate,trackingGate,rankQueue,normalizeMembership,summary,validateProgramme} from "../scripts/awin-autopilot.mjs";
const snapshot=JSON.parse(readFileSync(new URL("../data/awin/application-queue.json",import.meta.url),"utf8"));
const copy=x=>JSON.parse(JSON.stringify(x));
test("correct Awin counts; Active programme != Joined",()=>{
 const result=summary(snapshot);
 assert.deepEqual(result.counts,{joined:0,pending:1,notjoined:12,rejected:1,suspended:0});
 assert.equal(normalizeMembership("Not joined"),"notjoined");
 assert.equal(normalizeMembership("Active"),"unknown");
 assert.equal(normalizeMembership("Joined"),"joined");
});
test("never join already pending or rejected programmes",()=>{
 const p=snapshot.programmes.find(p=>p.id===30859);
 assert.equal(applicationGate(p).reason,"already_pending");
 const w=snapshot.programmes.find(p=>p.id===107764);
 assert.equal(applicationGate(w).reason,"rejected_review_required");
});
test("all five prioritized applications require verified site and programme terms",()=>{
 const queue=rankQueue(snapshot);
 assert.equal(queue.length,5);
 assert.ok(queue.every(p=>p.gate.allowed===false));
 assert.ok(queue.every(p=>p.gate.reason==="publisher_site_unverified"));
});
test("only reviewed, truthful applications can proceed to authenticated browser",()=>{
 const p=copy(snapshot.programmes.find(p=>p.id===25829));
 p.publisherSiteVerified=true;assert.equal(applicationGate(p).reason,"advertiser_terms_unreviewed");
 p.termsReviewed=true;assert.deepEqual(applicationGate(p),{allowed:true,reason:"ready_for_authorized_browser_join"});
 p.status="pending";assert.equal(applicationGate(p).reason,"already_pending");
});
test("never claim valid affiliate tracking without JOINED and verification",()=>{
 const p=copy(snapshot.programmes.find(p=>p.id===25829));
 assert.equal(trackingGate(p).reason,"not_joined");
 p.status="joined";assert.equal(trackingGate(p).reason,"commission_not_confirmed");
 p.commissionConfirmed=true;assert.equal(trackingGate(p).reason,"tracking_not_verified");
 p.trackingVerified=true;assert.equal(trackingGate(p).allowed,true);
});
test("Unicode note limit and duplicate advertiser IDs enforced",()=>{
 const p=copy(snapshot.programmes.find(p=>p.id===25829));p.reasonGreek="α".repeat(151);
 assert.throws(()=>validateProgramme(p),/150 Unicode/);
 const cloned=copy(snapshot);cloned.programmes.push(copy(cloned.programmes[0]));
 assert.throws(()=>rankQueue(cloned),/duplicate programme/);
});
