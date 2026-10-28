import test from "node:test";import assert from "node:assert/strict";import {eligible,safeAwinUrl,selectOffers} from "../lib/policy.mjs";
const now=Date.parse("2026-10-28T12:00:00Z");
const base={id:"1",title:"Test",price_eur:120,expected_commission_eur:12,currency:"EUR",in_stock:true,is_published:true,tracking_url:"https://www.awin1.com/cread.php?x=1",verified_at:"2026-10-28T10:00:00Z",tire_width:205,tire_profile:55,rim_diameter:16,season:"summer"};
test("allowlist prevents open redirects",()=>{assert.equal(safeAwinUrl("https://awin1.com.evil.com/x"),null);assert.equal(safeAwinUrl("http://awin1.com/x"),null);assert.ok(safeAwinUrl(base.tracking_url));});
test("commission and freshness guard",()=>{assert.ok(eligible(base,now));assert.equal(eligible({...base,is_published:false},now),false);assert.equal(eligible({...base,expected_commission_eur:2},now),false);assert.equal(eligible({...base,verified_at:"2026-10-20T10:00:00Z"},now),false);});
test("exact tyre matching and 3 max",()=>{const q={tire_width:205,tire_profile:55,rim_diameter:16,season:"summer"};assert.equal(selectOffers([base,{...base,id:"2",rim_diameter:17}],q,now).length,1);assert.deepEqual(selectOffers([],q,now),[]);});
