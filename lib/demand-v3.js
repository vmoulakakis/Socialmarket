const clamp=(v,min=0,max=1)=>Math.max(min,Math.min(max,Number(v)));
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=a=>a.length?a.reduce((s,v)=>s+Number(v||0),0)/a.length:null;

export function trap(x,a,b,c,d){
 if(!finite(x)) return null;
 x=Number(x);
 if(x<=a||x>=d) return (x===a&&a===b)||(x===d&&c===d)?1:0;
 if(x>=b&&x<=c) return 1;
 if(x>a&&x<b) return clamp((x-a)/(b-a));
 if(x>c&&x<d) return clamp((d-x)/(d-c));
 return 0;
}
export function tri(x,a,b,c){
 if(!finite(x)) return null;
 x=Number(x); if(x<=a||x>=c)return x===b?1:0; if(x===b)return 1; return x<b?clamp((x-a)/(b-a)):clamp((c-x)/(c-b));
}
const and=(...xs)=>xs.some(x=>x===null)?null:Math.min(...xs);
const or=(...xs)=>Math.max(...xs.filter(x=>x!==null),0);

export function historyDiagnostics(history=[]){
 const rows=[...history].filter(x=>x?.observed_at).sort((a,b)=>new Date(a.observed_at)-new Date(b.observed_at));
 const uniqueDays=new Set(rows.map(x=>String(x.observed_at).slice(0,10))).size;
 const first=rows[0]||null,last=rows.at(-1)||null;
 const delta=(k)=>finite(first?.[k])&&finite(last?.[k])?Number(last[k])-Number(first[k]):null;
 const spanDays=first&&last?Math.max(0,(new Date(last.observed_at)-new Date(first.observed_at))/86400000):0;
 return {points:rows.length,unique_days:uniqueDays,span_days:Number(spanDays.toFixed(2)),first_at:first?.observed_at||null,last_at:last?.observed_at||null,descriptive_delta:{demand:delta('demand_score'),competition:delta('competition_score'),pain:delta('pain_gap_score'),opportunity:delta('opportunity_score')},note:'Descriptive history only; deltas are not forecasts.'};
}

export function forecastReadiness(history=[],config={minimum_points:90,minimum_span_days:30,minimum_backtest_windows:3}){
 const h=historyDiagnostics(history),reasons=[];
 if(h.points<config.minimum_points) reasons.push(`needs_${config.minimum_points}_points`);
 if(h.span_days<config.minimum_span_days) reasons.push(`needs_${config.minimum_span_days}_day_span`);
 return {
  eligible:reasons.length===0,status:reasons.length?'WITHHELD':'SHADOW_BACKTEST_ELIGIBLE',reasons,history:h,production_promotion:false,
  temporal_tiers:{descriptive:h.points>0,statistical_shadow:h.unique_days>=14,change_point:h.unique_days>=14,neural_shadow:h.unique_days>=60&&h.span_days>=45,production_gate:h.points>=config.minimum_points&&h.span_days>=config.minimum_span_days},
  rule:'Complex models remain challengers until chronological backtests beat naive/statistical baselines with calibrated uncertainty.'
 };
}

export function evidenceQuality(evidence=[]){
 const rows=Array.isArray(evidence)?evidence:[];
 const domains=new Set(rows.map(x=>x.source_domain).filter(Boolean));
 const sourceKinds=new Set(rows.map(x=>x.source_kind).filter(Boolean));
 const platforms=new Set(rows.map(x=>x.platform).filter(Boolean));
 const scores=rows.map(x=>Number(x?.retrieval?.score)).filter(Number.isFinite);
 const authority=rows.map(x=>Number(x?.retrieval?.authority)).filter(Number.isFinite);
 const recency=rows.map(x=>Number(x?.retrieval?.recency)).filter(Number.isFinite);
 const confidence=rows.map(x=>Number(x?.confidence)).filter(Number.isFinite);
 const direct=rows.filter(x=>Number(x?.retrieval?.direct||0)>0).length;
 const validated=rows.filter(x=>String(x?.validation_status||'').toLowerCase()==='validated').length;
 const explicitContradictions=rows.filter(x=>x?.metadata?.contradiction===true||x?.metadata?.stance==='contradicting').length;
 const counts={};for(const r of rows){const d=r.source_domain||'unknown';counts[d]=(counts[d]||0)+1}
 const total=rows.length,domainHhi=total?Object.values(counts).reduce((s,c)=>s+(c/total)**2,0):null;
 return {observations:rows.length,independent_domains:domains.size,source_kinds:[...sourceKinds],platforms:[...platforms],direct_taxonomy_rows:direct,validated_rows:validated,validated_share:total?validated/total:null,domain_hhi:domainHhi,mean_retrieval:mean(scores),mean_authority:mean(authority),mean_recency:mean(recency),mean_confidence:mean(confidence),explicit_contradictions:explicitContradictions,contradiction_semantics:explicitContradictions?'explicit_metadata_only':'not_measured_unless_explicit'};
}

export function supplyDiagnostics(supply=[]){
 const rows=Array.isArray(supply)?supply:[];
 const merchants=new Map(); for(const r of rows) if(r.merchant_id&&!merchants.has(r.merchant_id)) merchants.set(r.merchant_id,r);
 const unique=[...merchants.values()];
 const trust=mean(unique.map(x=>x.trust_score).filter(finite));
 const commercial=mean(unique.map(x=>x.commercial_score).filter(finite));
 const research=mean(unique.map(x=>x.research_confidence).filter(finite));
 const competition=mean(unique.map(x=>x.competition_intensity_score).filter(finite));
 const riskRate=unique.length?unique.filter(x=>x.risk_flag===true).length/unique.length:null;
 const countStrength=1-Math.exp(-unique.length/8);
 const qualityParts=[trust===null?null:clamp(trust/100),commercial===null?null:clamp(commercial/100),research===null?null:clamp(research<=1?research:research/100),countStrength].filter(x=>x!==null);
 const strength=qualityParts.length?mean(qualityParts):null;
 return {merchant_count:unique.length,program_rows:rows.length,avg_trust:trust,avg_commercial:commercial,avg_research_confidence:research,avg_competition_intensity:competition,risk_rate:riskRate,analytical_supply_strength:strength===null?null:Number((strength*100).toFixed(1)),semantics:'DERIVED exact-taxonomy solution coverage; not market share and never a demand modifier.'};
}

export function fuzzyMarketState(context={}){
 const m=context.market||{},s=supplyDiagnostics(context.supply_context||[]),q=evidenceQuality(context.retrieved_evidence||[]);
 const demand=finite(m.demand_score)?Number(m.demand_score):null,competition=finite(m.competition_score)?Number(m.competition_score):null,pain=finite(m.pain_gap_score)?Number(m.pain_gap_score):null,confidence=finite(m.confidence)?Number(m.confidence)*(Number(m.confidence)<=1?100:1):null,supply=s.analytical_supply_strength;
 const dHigh=trap(demand,55,72,100,100),dMid=tri(demand,25,55,82),cLow=trap(competition,0,0,30,55),cHigh=trap(competition,50,72,100,100),pHigh=trap(pain,48,68,100,100),confHigh=trap(confidence,55,72,100,100),confLow=trap(confidence,0,0,45,65),sLow=trap(supply,0,0,30,58),sHigh=trap(supply,48,70,100,100);
 const states={
  validated_unmet_need:and(dHigh,pHigh,confHigh),
  whitespace:and(dHigh,sLow,cLow,confHigh),
  emerging:and(or(dMid,dHigh),sLow,confHigh),
  crowded_demand:and(dHigh,or(cHigh,sHigh),confHigh),
  balanced:and(or(dMid,dHigh),or(sHigh,tri(supply,25,55,80)),confHigh),
  uncertain:or(confLow,competition===null?1:0,pain===null?0.75:0,q.observations<3?0.85:0)
 };
 const ranked=Object.entries(states).map(([name,value])=>[name,value===null?0:value]).sort((a,b)=>b[1]-a[1]);
 return {state:ranked[0]?.[0]||'uncertain',membership:Object.fromEntries(ranked.map(([k,v])=>[k,Number(v.toFixed(3))])),inputs:{canonical_demand:demand,canonical_competition:competition,canonical_pain:pain,canonical_confidence:confidence,derived_supply_strength:supply},semantics:'DERIVED fuzzy state. Canonical market metrics are read-only.'};
}

export function fuzzyWhitespace(context={}){
 const m=context.market||{},s=supplyDiagnostics(context.supply_context||[]);
 const demand=finite(m.demand_score)?Number(m.demand_score):null,pain=finite(m.pain_gap_score)?Number(m.pain_gap_score):null,competition=finite(m.competition_score)?Number(m.competition_score):null,supply=s.analytical_supply_strength;
 if(demand===null||pain===null)return {status:'UNAVAILABLE',score:null,reason:'demand_and_pain_required',canonical_demand_unchanged:demand,rules:[]};
 const confidence=finite(m.confidence)?Number(m.confidence)*(Number(m.confidence)<=1?100:1):0;
 const dHigh=trap(demand,50,72,100,100)||0,dMid=tri(demand,25,55,82)||0,pHigh=trap(pain,45,68,100,100)||0;
 const sLow=supply===null?null:trap(supply,0,0,28,58),sHigh=supply===null?null:trap(supply,48,72,100,100);
 const cLow=competition===null?null:trap(competition,0,0,30,58),cHigh=competition===null?null:trap(competition,48,72,100,100);
 const rules=[];const add=(rule,activation,target)=>{if(activation!==null&&activation>0)rules.push({rule,activation:Number(activation.toFixed(3)),target})};
 if(sLow!==null){add('high demand + high pain + low supply',Math.min(dHigh,pHigh,sLow),94);add('medium/high demand + high pain + low supply',Math.min(Math.max(dMid,dHigh),pHigh,sLow),80)}
 if(cLow!==null)add('high demand + high pain + low competition',Math.min(dHigh,pHigh,cLow),90);
 if(sHigh!==null)add('high demand + strong supply',Math.min(dHigh,sHigh),46);
 if(cHigh!==null)add('high demand + strong competition',Math.min(dHigh,cHigh),42);
 add('high demand + high pain',Math.min(dHigh,pHigh),72);add('medium demand + pain',Math.min(Math.max(dMid,.05),Math.max(pHigh,.05)),56);
 if(!rules.length)return {status:'UNAVAILABLE',score:null,reason:'no_active_rules',canonical_demand_unchanged:demand,rules:[]};
 const raw=rules.reduce((sum,r)=>sum+r.activation*r.target,0)/rules.reduce((sum,r)=>sum+r.activation,0),certainty=.55+.45*clamp(confidence/100),score=clamp(raw*certainty,0,100);
 return {status:'INFERRED',score:Number(score.toFixed(2)),raw_rule_score:Number(raw.toFixed(2)),certainty_multiplier:Number(certainty.toFixed(3)),rules:[...rules].sort((a,b)=>b.activation-a.activation),canonical_demand_unchanged:demand,semantics:'INFERRED solution whitespace; supply/competition change exploitability, never observed demand.'};
}

export function jobsToBeDone(pains=[]){
 const rows=Array.isArray(pains)?pains:[];
 const markers={price_constraint:['ακριβ','φθην','οικονομ','τιμή','κόστος'],availability_constraint:['δεν βρίσκ','διαθέσι','εξαντ','availability'],delivery_constraint:['παράδο','μεταφορ','shipping','αποστολ'],trust_constraint:['απάτ','εμπιστ','επιστροφ','εγγύη','refund'],simplicity_desire:['εύκολ','απλ','setup','ρύθμι'],alternative_request:['εναλλακ','χωρίς συνδρομ','alternative'],fit_or_variant:['μέγεθος','χρώμα','μικρ','μεγαλ','variant']};
 const facets=[];for(const p of rows){const text=String(p.canonical_text||p.representative_pain||p.cluster_label||'').toLowerCase(),hits=Object.entries(markers).filter(([,terms])=>terms.some(t=>text.includes(t))).map(([name])=>name);if(hits.length)facets.push({pain_id:p.id||null,text:text.slice(0,500),facets:hits,severity:p.pain_severity??null,confidence:p.confidence??null})}
 const counts=Object.fromEntries(Object.keys(markers).map(name=>[name,facets.filter(f=>f.facets.includes(name)).length]));
 return {status:rows.length?'DERIVED':'UNAVAILABLE',validated_pain_count:rows.length,facets:facets.slice(0,25),facet_counts:counts,semantics:'Lexical JTBD routing from validated pain text; AI may interpret but may not invent pain evidence.'};
}

export function evidenceGraph(context={}){
 const root=`taxonomy:${context.taxonomy_id||context.market?.taxonomy_id||'unknown'}`,nodes=[{id:root,type:'taxonomy',label:context.market?.subcategory_name||context.market?.category_name||context.market?.taxonomy_name||'taxonomy'}],edges=[],seen=new Set([root]);
 const addNode=n=>{if(!seen.has(n.id)){seen.add(n.id);nodes.push(n)}};
 list(context.retrieved_evidence).slice(0,50).forEach((e,i)=>{const id=`evidence:${e.id||i}`;addNode({id,type:'evidence',label:e.title||e.source_domain||'evidence',domain:e.source_domain||null,confidence:e.confidence??null});edges.push({source:root,target:id,relation:'SUPPORTED_BY',weight:e.retrieval?.score??null})});
 list(context.validated_pains).slice(0,25).forEach((p,i)=>{const id=`pain:${p.id||i}`;addNode({id,type:'pain',label:p.canonical_text||p.representative_pain||p.cluster_label||'pain',severity:p.pain_severity??null});edges.push({source:root,target:id,relation:'HAS_VALIDATED_PAIN'})});
 list(context.supply_context).slice(0,35).forEach((m,i)=>{const id=`merchant:${m.merchant_id||i}`;addNode({id,type:'merchant',label:m.canonical_name||'merchant',trust:m.trust_score??null,risk:m.risk_flag??null});edges.push({source:root,target:id,relation:'HAS_SUPPLY',weight:m.research_confidence??null})});
 const q=evidenceQuality(context.retrieved_evidence||[]);
 return {status:'DERIVED',pattern:'lightweight_graph_rag_v31',nodes,edges,summary:{node_count:nodes.length,edge_count:edges.length,independent_domains:q.independent_domains,domain_hhi:q.domain_hhi,explicit_contradictions:q.explicit_contradictions},semantics:'Evidence graph for lineage/retrieval only; graph density is not demand.'};
}

function list(v){return Array.isArray(v)?v:[]}
export function causalReadiness(context={}){
 const h=historyDiagnostics(context.history||[]),alternatives=[];
 const q=evidenceQuality(context.retrieved_evidence||[]),s=supplyDiagnostics(context.supply_context||[]);
 if(q.independent_domains<=2&&q.observations)alternatives.push({hypothesis:'source_concentration',why:'Evidence may be overrepresented by too few independent domains.'});
 if(s.merchant_count)alternatives.push({hypothesis:'supply_visibility_bias',why:'More merchant pages can create more discoverable evidence without a demand change.'});
 if(h.span_days<30)alternatives.push({hypothesis:'short_history_regime',why:'Movement may reflect collection/research-cycle changes rather than market movement.'});
 alternatives.push({hypothesis:'seasonality_or_event_confounder',why:'Greek seasonality/events/promotions may jointly move evidence and supply.'});
 alternatives.push({hypothesis:'collector_or_query_change',why:'Collector coverage or alias changes can move evidence density.'});
 return {status:h.points>=60?'CAUSAL_CANDIDATE_NEEDS_EXOGENOUS_DATA':'WITHHELD',can_claim_causality:false,history_points:h.points,history_span_days:h.span_days,requirements:['explicit causal DAG','treatment/outcome definition','>=2 aligned exogenous/control series','identification','placebo/data-subset refutation','sensitivity analysis'],alternative_explanations:alternatives,semantics:'Correlation remains non-causal until explicit identification and refutation pass.'};
}

export function deriveDemandV3(context={},config={}){
 const evidence=evidenceQuality(context.retrieved_evidence||[]),supply=supplyDiagnostics(context.supply_context||[]),fuzzy=fuzzyMarketState(context),whitespace=fuzzyWhitespace(context),forecast=forecastReadiness(context.history||[],config.forecast||{}),jtbd=jobsToBeDone(context.validated_pains||[]),graph=evidenceGraph(context),causal=causalReadiness(context);
 const m=context.market||{};
 return {
  version:'deep_demand_v31',
  contract:{canonical_metrics_read_only:true,missing_remains_missing:true,observed_is_not_modeled:true,demand_supply_separate:true,correlation_is_not_causation:true},
  market:{taxonomy_id:context.taxonomy_id||m.taxonomy_id||null,category:m.category_name||null,subcategory:m.subcategory_name||null,demand_score:m.demand_score??null,competition_score:m.competition_score??null,pain_gap_score:m.pain_gap_score??null,opportunity_score:m.opportunity_score??null,confidence:m.confidence??null,observed_at:m.observed_at??null},
  evidence_quality:evidence,
  supply,
  fuzzy_state:fuzzy,
  fuzzy_whitespace:whitespace,
  jobs_to_be_done:jtbd,
  graph_rag:graph,
  causal_skeptic:causal,
  history:forecast.history,
  forecast_gate:forecast,
  demand_supply_tension:{state:fuzzy.state,demand:m.demand_score??null,supply_strength:supply.analytical_supply_strength,competition:m.competition_score??null,whitespace_score:whitespace.score,semantics:'Demand and supply are juxtaposed as separate dimensions. Supply never modifies demand.'}
 };
}
