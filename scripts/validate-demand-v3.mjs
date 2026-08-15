import assert from 'node:assert/strict';
import {deriveDemandV3,forecastReadiness,fuzzyMarketState,historyDiagnostics} from '../lib/demand-v3.js';

const base={
 taxonomy_id:'00000000-0000-0000-0000-000000000001',
 market:{taxonomy_id:'00000000-0000-0000-0000-000000000001',category_name:'Test',subcategory_name:'Sub',demand_score:78,competition_score:null,pain_gap_score:null,opportunity_score:null,confidence:.81,observed_at:'2026-08-15T17:00:00Z'},
 retrieved_evidence:[{source_domain:'statistics.gr',confidence:.9,retrieval:{score:.88,authority:1,recency:.9}},{source_domain:'example.gr',confidence:.7,retrieval:{score:.62,authority:.58,recency:.8}}],
 supply_context:[{merchant_id:'1',trust_score:80,commercial_score:70,research_confidence:.8,risk_flag:false}],
 history:[
  {observed_at:'2026-08-14T20:00:00Z',demand_score:70,competition_score:null,pain_gap_score:null,opportunity_score:null},
  {observed_at:'2026-08-15T17:00:00Z',demand_score:78,competition_score:null,pain_gap_score:null,opportunity_score:null}
 ]
};
const out=deriveDemandV3(base,{forecast:{minimum_points:90,minimum_span_days:30}});
assert.equal(out.market.demand_score,78,'canonical demand must be copied, not recalculated');
assert.equal(out.market.competition_score,null,'missing competition must remain null');
assert.equal(out.market.pain_gap_score,null,'missing pain must remain null');
assert.equal(out.forecast_gate.status,'WITHHELD','neural forecast must be withheld for shallow history');
assert.equal(out.forecast_gate.production_promotion,false);
assert.ok(out.fuzzy_state.membership.uncertain>=.75,'missing competition/pain must increase uncertainty');
assert.equal(out.contract.canonical_metrics_read_only,true);
assert.equal(out.contract.missing_remains_missing,true);
const h=historyDiagnostics(base.history);assert.equal(h.points,2);assert.equal(h.descriptive_delta.demand,8);
const gate=forecastReadiness(base.history,{minimum_points:90,minimum_span_days:30});assert.equal(gate.eligible,false);
const fuzzy=fuzzyMarketState(base);assert.equal(fuzzy.semantics,'DERIVED fuzzy state. Canonical market metrics are read-only.');
console.log('Demand Intelligence V3 invariants: OK');
