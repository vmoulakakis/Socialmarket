import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import postgres from "npm:postgres@3.4.5";
import { createClient } from "npm:@supabase/supabase-js@2.57.4";

/**
 * SocialMarket AI 3.0: private, read-only opportunity evidence API.
 * No Linkwise import, commission approval, background agent or paid model invocation.
 * Candidate source relationships must not be represented as validated demand.
 */
const HEADERS={"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"};
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:HEADERS});
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
Deno.serve(async(req:Request)=>{
 if(req.method!=="POST")return reply({error:"method_not_allowed"},405);
 const incoming=req.headers.get("authorization")||"";
 const token=incoming.match(/^Bearer\s+(\S+)$/i)?.[1];
 if(!token)return reply({error:"admin_session_required"},401);
 const url=Deno.env.get("SUPABASE_URL"),key=Deno.env.get("SUPABASE_ANON_KEY");
 const dbUrl=Deno.env.get("SUPABASE_DB_URL");
 if(!url||!key||!dbUrl)return reply({error:"runtime_not_configured"},503);
 const sb=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
 const {data,error}=await sb.auth.getUser(token);
 const allowedAdmin=(Deno.env.get("SOCIALMARKET_ARCHITECT_ADMIN_EMAIL")||"vmoulakakis@gmail.com").toLowerCase();
 if(error||!data.user||data.user.email?.toLowerCase()!==allowedAdmin)return reply({error:"admin_only"},403);
 const raw=await req.text();
 if(raw.length>1200)return reply({error:"payload_too_large"},413);
 let body:Record<string,unknown>;
 try{body=JSON.parse(raw)}catch{return reply({error:"invalid_json"},400)}
 const action=body.action==="brief"?"brief":body.action==="diagnostic"?"diagnostic":"overview";
 if(action==="brief" && (typeof body.problem_id!=="string"||!UUID.test(body.problem_id)))return reply({error:"invalid_problem_id"},400);
 const sql=postgres(dbUrl,{max:1,prepare:false,connect_timeout:5,ssl:"require",idle_timeout:5});
 try{
  if(action==="brief"){
   const out=await sql`select sm_intel.opportunity_brief_v3(${body.problem_id}::uuid) as value`;
   if(!out[0]?.value)return reply({error:"problem_not_found"},404);
   return reply({ok:true,contract:"sm_intel_opportunity_v3",brief:out[0].value,
     validation:"evidence_candidate_only",commercial_actions_permitted:false});
  }
  const [summary,models,neural]=await Promise.all([
   sql`select r.evidence_status,count(*)::integer n from sm_intel.opportunity_research_v3 r group by r.evidence_status order by r.evidence_status`,
   sql`select model_id,task_kind,vector_dimensions,runtime,status from sm_intel.neural_model_registry_v3 order by model_id`,
   sql`select sm_intel.embedding_health_v3() as value`
  ]);
  if(action==="diagnostic"){
   const alerts=await sql`select r.problem_cluster_id,p.problem_title,p.category,
    r.demand_sources,r.supply_sources,r.counter_sources,
    r.verified_demand_sources,r.verified_supply_sources,
    r.evidence_status,r.research_gaps
    from sm_intel.opportunity_research_v3 r
    join public.market_problem_clusters p on p.id=r.problem_cluster_id
    where r.evidence_status<>'ready_for_independent_review'
    order by r.demand_sources+r.supply_sources desc,p.problem_title limit 15`;
   return reply({ok:true,contract:"sm_intel_opportunity_v3",status:summary,
     neural:neural[0]?.value,models,gaps:alerts,alerts_are_evidence_gaps:true});
  }
  const problems=await sql`select r.problem_cluster_id,p.problem_title,p.category,
   r.evidence_status,r.demand_sources,r.supply_sources,r.counter_sources,
   r.verified_demand_sources,r.verified_supply_sources,
   r.distinct_verified_demand_domains,r.distinct_verified_supply_domains,
   r.research_gaps,
   (select count(*)::integer from sm_intel.opportunity_product_candidates_v3 c
      where c.problem_cluster_id=r.problem_cluster_id) candidate_products
   from sm_intel.opportunity_research_v3 r
   join public.market_problem_clusters p on p.id=r.problem_cluster_id
   order by case r.evidence_status when 'ready_for_independent_review' then 0
       when 'partial_evidence' then 1 else 2 end,
     r.demand_sources+r.supply_sources+r.counter_sources desc,p.problem_title
   limit 50`;
  return reply({ok:true,contract:"sm_intel_opportunity_v3",scope:"Greece",status:summary,
    neural:neural[0]?.value,models,opportunities:problems,
    research_status:"no_verified_high_demand_low_supply_claim_without_independent_evidence",
    commercial_actions_permitted:false,
    note:"Full Linkwise feed import remains disabled by user request"});
 }catch{return reply({error:"intelligence_backend_unavailable"},503)}
 finally{await sql.end({timeout:2}).catch(()=>{})}
});
