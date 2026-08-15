import assert from 'node:assert/strict';
import {deriveDemandV3,forecastReadiness,fuzzyMarketState,historyDiagnostics,fuzzyWhitespace,evidenceGraph,causalReadiness,jobsToBeDone} from '../lib/demand-v3.js';

const base={
 taxonomy_id:'00000000-0000-0000-0000-000000000001',
 market:{taxonomy_id:'00000000-0000-0000-0000-000000000001',category_name:'Test',subcategory_name:'Sub',demand_score:78,competition_score:null,pain_gap_score:null,opportunity_score:null,confidence:.81,observed_at:'2026-08-15T17:00:00Z'},
 retrieved_evidence:[
  {id:'e1',source_domain:'statistics.gr',confidence:.9,validation_status:'validated',retrieval:{score:.88,authority:1,recency:.9}},
  {id:'e2',source_domain:'example.gr',confidence:.7,validation_status:'validated',retrieval:{score:.62,authority:.58,recency:.8}}
 ],
 supply_context:[{merchant_id:'1',canonical_name:'Merchant',trust_score:80,commercial_score:70,research_confidence:.8,risk_flag:false}],
 validated_pains:[],
 history:[
  {observed_at:'2026-08-14T20:00:00Z',demand_score:70,competition_score:null,pain_gap_score:null,opportunity_score:null},
  {observed_at:'2026-08-15T17:00:00Z',demand_score:78,competition_score:null,pain_gap_score:null,opportunity_score:null}
 ]
};
const out=deriveDemandV3(base,{forecast:{minimum_points:90,minimum_span_days:30}});
assert.equal(out.version,'deep_demand_v31');
assert.equal(out.market.demand_score,78,'canonical demand must be copied, not recalculated');
assert.equal(out.market.competition_score,null,'missing competition must remain null');
assert.equal(out.market.pain_gap_score,null,'missing pain must remain null');
assert.equal(out.forecast_gate.status,'WITHHELD','production forecast must be withheld for shallow history');
assert.equal(out.forecast_gate.production_promotion,false);
assert.equal(out.forecast_gate.temporal_tiers.neural_shadow,false);
assert.ok(out.fuzzy_state.membership.uncertain>=.75,'missing competition/pain must increase uncertainty');
assert.equal(out.contract.canonical_metrics_read_only,true);
assert.equal(out.contract.missing_remains_missing,true);
assert.equal(out.contract.demand_supply_separate,true);
assert.equal(out.contract.correlation_is_not_causation,true);
assert.equal(out.demand_supply_tension.demand,78,'supply must not modify canonical demand');
const h=historyDiagnostics(base.history);assert.equal(h.points,2);assert.equal(h.descriptive_delta.demand,8);
const gate=forecastReadiness(base.history,{minimum_points:90,minimum_span_days:30});assert.equal(gate.eligible,false);
const fuzzy=fuzzyMarketState(base);assert.equal(fuzzy.semantics,'DERIVED fuzzy state. Canonical market metrics are read-only.');
const missing=fuzzyWhitespace(base);assert.equal(missing.status,'UNAVAILABLE','pain missing must fail closed');

const comparable={...base,market:{...base.market,competition_score:24,pain_gap_score:76},supply_context:[{merchant_id:'1',trust_score:75,commercial_score:65,research_confidence:.8,risk_flag:false}]};
const lowSupply=fuzzyWhitespace(comparable);
const highSupply=fuzzyWhitespace({...comparable,supply_context:Array.from({length:30},(_,i)=>({merchant_id:String(i+1),trust_score:90,commercial_score:90,research_confidence:.95,risk_flag:false}))});
assert.equal(lowSupply.canonical_demand_unchanged,78);
assert.equal(highSupply.canonical_demand_unchanged,78);
assert.ok(lowSupply.score>highSupply.score,'stronger supply may lower whitespace, never demand');
assert.ok(lowSupply.rules.some(r=>r.rule.includes('low competition')),'low competition rule requires a real competition value');
assert.ok(!fuzzyWhitespace({...comparable,market:{...comparable.market,competition_score:null}}).rules.some(r=>r.rule.includes('low competition')),'null competition must not become low competition');

const graph=evidenceGraph(comparable);
assert.equal(graph.status,'DERIVED');
assert.match(graph.semantics,/not demand/);
assert.ok(graph.summary.node_count>=4);
const causal=causalReadiness(comparable);assert.equal(causal.can_claim_causality,false);assert.equal(causal.status,'WITHHELD');
const jtbd=jobsToBeDone([{id:'p1',canonical_text:'Θέλω πιο οικονομική εναλλακτική χωρίς συνδρομή',pain_severity:80,confidence:.9}]);
assert.equal(jtbd.status,'DERIVED');assert.ok(jtbd.facet_counts.price_constraint>0);assert.ok(jtbd.facet_counts.alternative_request>0);
console.log('Deep Demand Intelligence V3.1 invariants: OK');
