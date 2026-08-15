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
 return {eligible:reasons.length===0,status:reasons.length?'WITHHELD':'SHADOW_BACKTEST_ELIGIBLE',reasons,history:h,production_promotion:false,rule:'Neural models remain challengers until chronological backtests beat naive baselines with calibrated uncertainty.'};
}

export function evidenceQuality(evidence=[]){
 const rows=Array.isArray(evidence)?evidence:[];
 const domains=new Set(rows.map(x=>x.source_domain).filter(Boolean));
 const scores=rows.map(x=>Number(x?.retrieval?.score)).filter(Number.isFinite);
 const authority=rows.map(x=>Number(x?.retrieval?.authority)).filter(Number.isFinite);
 const recency=rows.map(x=>Number(x?.retrieval?.recency)).filter(Number.isFinite);
 const confidence=rows.map(x=>Number(x?.confidence)).filter(Number.isFinite);
 const explicitContradictions=rows.filter(x=>x?.metadata?.contradiction===true||x?.metadata?.stance==='contradicting').length;
 return {observations:rows.length,independent_domains:domains.size,mean_retrieval:mean(scores),mean_authority:mean(authority),mean_recency:mean(recency),mean_confidence:mean(confidence),explicit_contradictions:explicitContradictions,contradiction_semantics:explicitContradictions?'explicit_metadata_only':'not_measured_unless_explicit'};
}

export function supplyDiagnostics(supply=[]){
 const rows=Array.isArray(supply)?supply:[];
 const merchants=new Map(); for(const r of rows) if(r.merchant_id&&!merchants.has(r.merchant_id)) merchants.set(r.merchant_id,r);
 const unique=[...merchants.values()];
 const trust=mean(unique.map(x=>x.trust_score).filter(finite));
 const commercial=mean(unique.map(x=>x.commercial_score).filter(finite));
 const research=mean(unique.map(x=>x.research_confidence).filter(finite));
 const riskRate=unique.length?unique.filter(x=>x.risk_flag===true).length/unique.length:null;
 const countStrength=1-Math.exp(-unique.length/8);
 const qualityParts=[trust===null?null:clamp(trust/100),commercial===null?null:clamp(commercial/100),research===null?null:clamp(research),countStrength].filter(x=>x!==null);
 const strength=qualityParts.length?mean(qualityParts):null;
 return {merchant_count:unique.length,avg_trust:trust,avg_commercial:commercial,avg_research_confidence:research,risk_rate:riskRate,analytical_supply_strength:strength===null?null:Number((strength*100).toFixed(1)),semantics:'DERIVED supply context from exact-taxonomy merchant/program intelligence; not a market-share estimate.'};
}

export function fuzzyMarketState(context={}){
 const m=context.market||{},s=supplyDiagnostics(context.supply_context||[]),q=evidenceQuality(context.retrieved_evidence||[]);
 const demand=finite(m.demand_score)?Number(m.demand_score):null,competition=finite(m.competition_score)?Number(m.competition_score):null,pain=finite(m.pain_gap_score)?Number(m.pain_gap_score):null,confidence=finite(m.confidence)?Number(m.confidence)*100:null,supply=s.analytical_supply_strength;
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

export function deriveDemandV3(context={},config={}){
 const evidence=evidenceQuality(context.retrieved_evidence||[]),supply=supplyDiagnostics(context.supply_context||[]),fuzzy=fuzzyMarketState(context),forecast=forecastReadiness(context.history||[],config.forecast||{});
 const m=context.market||{};
 return {
  contract:{canonical_metrics_read_only:true,missing_remains_missing:true,observed_is_not_modeled:true},
  market:{taxonomy_id:context.taxonomy_id||m.taxonomy_id||null,category:m.category_name||null,subcategory:m.subcategory_name||null,demand_score:m.demand_score??null,competition_score:m.competition_score??null,pain_gap_score:m.pain_gap_score??null,opportunity_score:m.opportunity_score??null,confidence:m.confidence??null,observed_at:m.observed_at??null},
  evidence_quality:evidence,
  supply,
  fuzzy_state:fuzzy,
  history:forecast.history,
  forecast_gate:forecast,
  demand_supply_tension:{state:fuzzy.state,demand:m.demand_score??null,supply_strength:supply.analytical_supply_strength,competition:m.competition_score??null,semantics:'Analytical juxtaposition only; supply never modifies demand.'}
 };
}
