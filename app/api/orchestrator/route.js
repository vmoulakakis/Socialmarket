import {NextResponse} from 'next/server';
import {timingSafeEqual} from 'node:crypto';
import {createClient} from '@supabase/supabase-js';
import {orchestrate,getSiteRegistry,resumeOrchestration} from '@/lib/orchestrator/runtime';
import {persistenceHealth} from '@/lib/orchestrator/store';
import {APPROVED_ADMIN_EMAIL,APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

export const runtime='nodejs';
export const maxDuration=30;
const MAX_PROMPT_CHARS=Number(process.env.ORCHESTRATOR_MAX_PROMPT_CHARS||6000);

function staticConfig(){return {
  databaseServiceRole:Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
  adminJwtSupported:true,
  llm:Boolean(process.env.DEEPSEEK_API_KEY||process.env.OPENROUTER_API_KEY),
  secretAuth:Boolean(process.env.ORCHESTRATOR_SECRET),
  toolQueue:true,
  githubExecutor:true
}}
function bearer(req){const h=req.headers.get('authorization')||'';return h.startsWith('Bearer ')?h.slice(7):''}
function secretMatches(token){const secret=process.env.ORCHESTRATOR_SECRET;if(!secret||!token)return false;const a=Buffer.from(token),b=Buffer.from(secret);return a.length===b.length&&timingSafeEqual(a,b)}
async function authorized(req){
 const token=bearer(req);if(!token)return {ok:false,status:401,error:'unauthorized'};
 if(secretMatches(token))return {ok:true,mode:'orchestrator-secret',accessToken:null};
 const authClient=createClient(APPROVED_SUPABASE_URL,APPROVED_PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
 const {data,error}=await authClient.auth.getUser(token);const email=String(data?.user?.email||'').toLowerCase();
 if(error||email!==APPROVED_ADMIN_EMAIL.toLowerCase())return {ok:false,status:401,error:'unauthorized'};
 return {ok:true,mode:'admin-jwt',accessToken:token};
}
function httpStatus(run){return ['WAITING_APPROVAL','WAITING_TOOL'].includes(run.state)?202:run.state==='FAILED'?500:200}

export async function GET(req){
 const token=bearer(req);let auth=null;
 if(token){auth=await authorized(req);if(!auth.ok)return NextResponse.json({error:auth.error},{status:auth.status})}
 const runId=req.nextUrl.searchParams.get('runId');
 if(runId){
  if(!auth?.ok)return NextResponse.json({error:'authentication_required'},{status:401});
  try{const approved=(req.nextUrl.searchParams.get('approved')||'').split(',').map(x=>x.trim()).filter(Boolean).slice(0,20);const run=await resumeOrchestration({runId,approvedCapabilities:approved,accessToken:auth.accessToken});return NextResponse.json(run,{status:httpStatus(run)})}catch(e){return NextResponse.json({error:String(e)},{status:400})}
 }
 const config=staticConfig();const persistence=await persistenceHealth(auth?.accessToken||null);const supervisedReady=persistence.ok&&config.llm&&(config.secretAuth||auth?.mode==='admin-jwt');
 return NextResponse.json({service:'SocialMarket Autonomous Commerce OS',status:supervisedReady?'supervised-agentic':'degraded',fullAutonomy:false,dependencies:{...config,persistence},limits:{maxPromptChars:MAX_PROMPT_CHARS,maxDurationSeconds:30},registry:getSiteRegistry()});
}

export async function POST(req){
 const auth=await authorized(req);if(!auth.ok)return NextResponse.json({error:auth.error},{status:auth.status});
 try{
  const body=await req.json();const approved=Array.isArray(body?.approvedCapabilities)?body.approvedCapabilities.slice(0,20):[];
  if(body?.runId){const run=await resumeOrchestration({runId:String(body.runId),approvedCapabilities:approved,accessToken:auth.accessToken});return NextResponse.json(run,{status:httpStatus(run)})}
  const prompt=typeof body?.prompt==='string'?body.prompt.trim():'';if(!prompt)return NextResponse.json({error:'prompt_required'},{status:400});if(prompt.length>MAX_PROMPT_CHARS)return NextResponse.json({error:'prompt_too_large',maxPromptChars:MAX_PROMPT_CHARS},{status:413});
  const run=await orchestrate({prompt,approvedCapabilities:approved,accessToken:auth.accessToken});return NextResponse.json(run,{status:httpStatus(run)});
 }catch(e){return NextResponse.json({error:String(e)},{status:400})}
}
