import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { createRemoteJWKSet, jwtVerify } from 'npm:jose@6.1.0'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

const sql=postgres(Deno.env.get('SUPABASE_DB_URL')!,{prepare:false,max:1})
const ISSUER='https://token.actions.githubusercontent.com'
const AUDIENCE='socialmarket-supabase-worker'
const REPOSITORY_ID='1329707883'
const REPOSITORY='vmoulakakis/Socialmarket'
const ALLOWED=new Set(['vmoulakakis/Socialmarket/.github/workflows/deep-demand-intelligence-v31.yml@refs/heads/main'])
const JWKS=createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`))
const json=(x:unknown,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{'content-type':'application/json','cache-control':'no-store'}})

async function auth(req:Request){
  const h=req.headers.get('authorization')||''
  if(!h.startsWith('Bearer ')) throw new Error('missing_oidc')
  const {payload}=await jwtVerify(h.slice(7),JWKS,{issuer:ISSUER,audience:AUDIENCE})
  if(String(payload.repository_id||'')!==REPOSITORY_ID||String(payload.repository||'')!==REPOSITORY||String(payload.ref||'')!=='refs/heads/main'||!ALLOWED.has(String(payload.workflow_ref||''))) throw new Error('oidc_not_allowed')
}

async function taxonomyList(){
  return await sql`select taxonomy_id,category_name,subcategory_name,taxonomy_name,observed_at,demand_score,competition_score,pain_gap_score,opportunity_score,confidence,methodology_version from api.semantic_category_market_v2 where taxonomy_id is not null order by opportunity_score desc nulls last,demand_score desc nulls last`
}

async function context(taxonomyId:string){
  const market=await sql`select * from api.semantic_category_market_v2 where taxonomy_id=${taxonomyId}::uuid limit 1`
  if(!market[0]) throw new Error('taxonomy_not_found')
  const history=await sql`select observed_at,demand_score,competition_score,pain_gap_score,satisfaction_score,opportunity_score,confidence,methodology_version from intel.category_market_snapshots where taxonomy_id=${taxonomyId}::uuid order by observed_at desc limit 365`
  const evidence=await sql`select id,entity_type,source_kind,platform,source_url,source_domain,title,left(body,1600) body,published_at,collected_at,confidence,validation_status,metrics,metadata from evidence.observations where entity_type='taxonomy' and entity_id=${taxonomyId}::uuid order by coalesce(published_at,collected_at) desc limit 80`
  const supply=await sql`select g.merchant_id,g.canonical_name,g.taxonomy_id,g.taxonomy_name,g.primary_category,g.primary_subcategory,g.opportunity_score,g.trust_score,g.complaint_risk_score,g.confidence,g.observed_at,mr.program_id,mr.program_name,mr.commercial_score,mr.commercial_confidence,mr.competition_intensity_score,mr.greek_market_fit_score,mr.deep_research_score,mr.research_confidence,mr.risk_flag,mr.risk_reason,mr.evidence_count,mr.researched_at from api.merchant_gap_rankings g left join api.merchant_rankings mr on mr.merchant_id=g.merchant_id where g.taxonomy_id=${taxonomyId}::uuid order by g.opportunity_score desc nulls last,g.trust_score desc nulls last limit 50`
  const pains=await sql`select id,canonical_text,category,subcategory,evidence_count,source_diversity,pain_severity,commercial_intent,audit_score,confidence,validation_status,metadata from public.validated_pain_clusters where category=${market[0].category_name} and (${market[0].subcategory_name}::text is null or subcategory=${market[0].subcategory_name}) order by pain_severity desc nulls last,evidence_count desc nulls last limit 40`
  return {taxonomy_id:taxonomyId,market:market[0],history:[...history].reverse(),retrieved_evidence:evidence,supply_context:supply,validated_pains:pains,retrieval_semantics:{method:'direct audited taxonomy evidence for autonomous model lab',does_not_modify_scores:true,missing_remains_missing:true}}
}

async function save(taxonomyId:string,analysis:any){
  if(!analysis||analysis.version!=='deep_demand_v31') throw new Error('invalid_analysis_version')
  const marketObserved=analysis?.observed?.observed_at||analysis?.generated_from_market_observed_at||null
  const temporal=analysis?.temporal_lab||{}
  const decision=String(temporal?.decision||'')
  const status=decision==='WITHHOLD_PRODUCTION_FORECAST'?'withheld':'completed'
  const rows=await sql`insert into intel.demand_model_lab_runs(taxonomy_id,geography,engine_version,status,source_market_observed_at,analysis,metadata) values(${taxonomyId}::uuid,'GR','deep_demand_v31',${status},${marketObserved},${sql.json(analysis)},${sql.json({worker:'github-actions',authentication:'github_oidc',canonical_metrics_read_only:true})}) returning id,generated_at`
  return rows[0]
}

Deno.serve(async req=>{
  if(req.method==='GET') return json({ok:true,service:'demand-model-lab-gateway',version:'3.1',max_db_connections_per_instance:1})
  if(req.method!=='POST') return json({error:'method_not_allowed'},405)
  try{
    await auth(req)
    const body=await req.json(),action=String(body.action||'')
    if(action==='taxonomy_list') return json({ok:true,items:await taxonomyList()})
    if(action==='context') return json({ok:true,context:await context(String(body.taxonomy_id||''))})
    if(action==='save') return json({ok:true,result:await save(String(body.taxonomy_id||''),body.analysis)})
    throw new Error('action_not_allowed')
  }catch(error){
    console.error(error)
    const message=String(error instanceof Error?error.message:error)
    return json({error:message},message.includes('oidc')?401:500)
  }
})
