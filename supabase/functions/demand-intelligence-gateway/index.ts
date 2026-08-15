import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import {createClient} from 'npm:@supabase/supabase-js@2.57.4'

const ADMIN='vmoulakakis@gmail.com'
const DEEPSEEK_KEY=Deno.env.get('DEEPSEEK_API_KEY')||Deno.env.get('DEEP_SEEK_API_KEY')||''
const MODEL=Deno.env.get('DEEPSEEK_MODEL')||'deepseek-v4-pro'
const SUPABASE_URL=Deno.env.get('SUPABASE_URL')!
const ANON_KEY=Deno.env.get('SUPABASE_ANON_KEY')!
const cors={'access-control-allow-origin':'*','access-control-allow-headers':'authorization, apikey, content-type','access-control-allow-methods':'GET,POST,OPTIONS'}
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{...cors,'content-type':'application/json','cache-control':'no-store'}})
function decodeJwt(token:string){const part=token.split('.')[1];if(!part)throw new Error('invalid_jwt');const normalized=part.replace(/-/g,'+').replace(/_/g,'/'),pad='='.repeat((4-normalized.length%4)%4);return JSON.parse(atob(normalized+pad))}
async function deepseek(system:string,input:unknown,maxTokens=8200){if(!DEEPSEEK_KEY)throw new Error('deepseek_not_configured');const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${DEEPSEEK_KEY}`},body:JSON.stringify({model:MODEL,temperature:.06,max_tokens:maxTokens,response_format:{type:'json_object'},messages:[{role:'system',content:system},{role:'user',content:JSON.stringify(input)}]})});const raw=await r.text();if(!r.ok)throw new Error(`deepseek_${r.status}:${raw.slice(0,700)}`);const j=JSON.parse(raw),content=String(j?.choices?.[0]?.message?.content||'{}');return{data:JSON.parse(content),usage:j?.usage||{}}}

Deno.serve(async req=>{
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors})
 if(req.method==='GET')return json({ok:true,service:'demand-intelligence-gateway',version:'3.1',model:MODEL,deepseek_configured:Boolean(DEEPSEEK_KEY)})
 if(req.method!=='POST')return json({error:'method_not_allowed'},405)
 try{
  const auth=req.headers.get('authorization')||'';if(!auth.startsWith('Bearer '))throw new Error('missing_auth')
  const token=auth.slice(7),claims=decodeJwt(token);if(String(claims.email||'').toLowerCase()!==ADMIN)throw new Error('admin_only')
  const body=await req.json(),context=body.context||{},deterministic=body.deterministic||{}
  if(!context.taxonomy_id||!context.market)throw new Error('demand_context_required')
  const evidence=(Array.isArray(context.retrieved_evidence)?context.retrieved_evidence:[]).slice(0,55).map((x:any)=>({id:x.id,source_kind:x.source_kind,platform:x.platform,source_domain:x.source_domain,source_url:x.source_url,title:x.title,body:String(x.body||'').slice(0,1300),published_at:x.published_at,collected_at:x.collected_at,confidence:x.confidence,validation_status:x.validation_status,retrieval:x.retrieval,metrics:x.metrics,metadata:x.metadata}))
  const supply=(Array.isArray(context.supply_context)?context.supply_context:[]).slice(0,40)
  const history=(Array.isArray(context.history)?context.history:[]).slice(0,180)
  const pains=(Array.isArray(context.validated_pains)?context.validated_pains:[]).slice(0,30)
  const sourceMix=(Array.isArray(context.source_mix)?context.source_mix:[]).slice(0,30)
  const input={market:context.market,query:context.query,evidence,source_mix:sourceMix,supply,validated_pains:pains,history,deterministic,retrieval_semantics:context.retrieval_semantics,forecast_gate:deterministic.forecast_gate||context.forecast_gate}
  const system=`You are the SocialMarket Deep Demand Intelligence V3.1 research panel for Greece. You combine six specialist roles but must produce ONE coherent audited JSON dossier:
1) Greek Market Researcher — interpret only supplied Greek/public/official/open-web evidence and distinguish direct category evidence from contextual macro evidence.
2) Jobs-to-be-Done & Pain Analyst — identify desired outcomes, constraints, switching triggers, objections and alternative requests only when supported by validated pain/evidence.
3) Supply Structure Analyst — analyze exact-taxonomy merchant/program coverage, trust, commercial quality, fragmentation and risk. Supply is a SEPARATE dimension and can never lower or rewrite canonical demand.
4) Temporal Forecast Scientist — explain history sufficiency, regimes, change points/model readiness. If forecast gate is WITHHELD, do not invent a trajectory. Neural complexity is never evidence of accuracy.
5) Causal Skeptic — actively search for source-concentration, collector/query-change, supply-visibility, seasonality/event and selection-bias explanations. Correlation is never causation.
6) Executive Strategy Storyteller — compile the result as Kimi-quality business-analytics scenes: Question -> headline finding -> visual implication -> evidence -> uncertainty -> so what -> action.

ABSOLUTE TRUTH CONTRACT:
- Use ONLY the supplied production bundle.
- Canonical demand, competition, pain, opportunity and confidence are immutable. Quote them exactly or say missing.
- deterministic.fuzzy_whitespace is INFERRED exploitability, never demand.
- deterministic.graph_rag is lineage/retrieval context; graph density is never demand.
- Never invent search volume, market size/share, paid-ad spend/impressions, CPC/CTR, sales, prices, conversions, dates, Greek macro figures or social metrics.
- Linkwise/program KPIs are network baselines unless explicitly first-party.
- A registry/domain name alone is not a measurement.
- Missing remains missing; absence is not contradiction.
- If deterministic.forecast_gate.status is WITHHELD, all quantitative future forecasts must be WITHHELD.
- Causal claims remain WITHHELD unless explicit identification/refutation output is supplied and passed.
- Prefer evidence IDs/URLs/domain names in support fields. State the strongest alternative explanation for each major thesis.

Return strict JSON with this schema:
{
 executive_thesis:{headline,summary,confidence_0_100,confidence_basis,truth_label:'OBSERVED'|'DERIVED'|'INFERRED'},
 research_panel:{
  greek_market_researcher:{findings:[{finding,evidence_ids,source_domains,classification:'OBSERVED'|'DERIVED',limits}],missing_evidence},
  jobs_to_be_done:{jobs:[{job,desired_outcome,constraints,switching_trigger,evidence_ids,confidence_0_100}],pain_structure,limits},
  supply_analyst:{structure,coverage_strength,fragmentation_or_concentration,trust_quality,commercial_quality,risk,relationship_to_demand,limits},
  temporal_scientist:{regime,history_quality,change_point_status,statistical_status,neural_status,production_forecast_status,limits},
  causal_skeptic:{alternative_explanations:[{hypothesis,why_plausible,evidence_or_test}],causal_status,what_would_be_required},
  adversarial_auditor:{weak_links,contradictions,source_bias_risks,unsupported_interpretations_to_avoid}
 },
 market_state:{label,why,canonical_metrics,fuzzy_membership,fuzzy_whitespace:{score,status,meaning,top_rules}},
 demand_anatomy:[{dimension,assessment,evidence,confidence_0_100,classification:'OBSERVED'|'DERIVED'|'INFERRED',limits}],
 demand_supply_regime:{demand_state,supply_state,competition_state,pain_state,whitespace_state,interpretation,what_supply_does_not_mean},
 evidence_graph:{thesis_path:[{from,relation,to,why_it_matters}],source_concentration,contradiction_paths,limits},
 greek_context:[{finding,evidence,source,classification,limits}],
 contradictions:[{claim,supporting,contradicting,status:'explicit_conflict'|'weak_support'|'unresolved',impact}],
 confidence_decomposition:{source_diversity,authority,freshness,retrieval_quality,canonical_confidence,domain_concentration,missing_dimensions,overall_comment},
 forecast_lab:{status,baseline_status,statistical_challengers,neural_challengers,causal_status,production_forecast,why,next_gate},
 scenario_lab:[{scenario,assumption,expected_direction:'up'|'down'|'mixed'|'unknown',what_changes,what_does_not_change,evidence_needed,classification:'INFERRED'}],
 affiliate_implications:[{priority,implication,evidence,commercial_relevance,what_not_to_assume}],
 decision_board:[{priority,decision:'INVESTIGATE'|'TEST'|'PROMOTE'|'WAIT'|'REJECT'|'COLLECT_EVIDENCE',action,why,confidence_0_100,evidence_needed,metric_to_watch}],
 falsification_tests:[{thesis,test,would_falsify,cheapest_next_step}],
 next_evidence_to_collect:[{priority,evidence,source_family,why,expected_uncertainty_reduction}],
 presentation_scenes:[{order,title,headline,question,visual_type,evidence_summary,uncertainty,so_what,action,truth_label}],
 claim_audit:{observed_claims,derived_claims,inferred_claims,forecasted_claims,causal_candidates,withheld_claims,unsupported_claims_avoided}
}
Be specific and dense. Prefer 4-8 high-value items in important lists. Do not fill a list with generic advice when evidence is insufficient; use limits/withheld instead.`
  const r=await deepseek(system,input,9200)
  const sb=createClient(SUPABASE_URL,ANON_KEY,{global:{headers:{Authorization:`Bearer ${token}`}}})
  const evidenceIds=evidence.map((x:any)=>x.id).filter(Boolean)
  const {data:runId,error:saveError}=await sb.rpc('admin_save_demand_analysis_v3',{p_taxonomy_id:context.taxonomy_id,p_market_observed_at:context.market?.observed_at||null,p_data_contract:{canonical_metrics_read_only:true,missing_remains_missing:true,demand_supply_separate:true,correlation_is_not_causation:true,retrieval:context.retrieval_semantics||{},deterministic_version:deterministic?.version||null},p_analysis:r.data,p_evidence_ids:evidenceIds,p_status:'completed'})
  await sb.rpc('admin_ai_log',{p_task_type:'deep_demand_intelligence_v31',p_provider:'deepseek',p_model_name:MODEL,p_status:'success',p_input_tokens:Number(r.usage?.prompt_tokens||0),p_output_tokens:Number(r.usage?.completion_tokens||0),p_metadata:{taxonomy_id:context.taxonomy_id,run_id:runId||null,evidence_count:evidence.length,save_error:saveError?.message||null,forecast_status:deterministic?.forecast_gate?.status||null,graph_nodes:deterministic?.graph_rag?.nodes?.length||0}})
  return json({ok:true,model:MODEL,run_id:runId||null,analysis:r.data,usage:r.usage,persist_warning:saveError?.message||null,engine_version:'3.1'})
 }catch(e){const msg=String(e instanceof Error?e.message:e);return json({error:msg},msg.includes('admin_only')?403:400)}
})
