import {NextResponse} from 'next/server';
import {timingSafeEqual} from 'node:crypto';
import {orchestrate,getSiteRegistry} from '@/lib/orchestrator/runtime';
import {persistenceHealth} from '@/lib/orchestrator/store';

export const runtime='nodejs';
export const maxDuration=30;

const MAX_PROMPT_CHARS=Number(process.env.ORCHESTRATOR_MAX_PROMPT_CHARS||6000);

function staticConfig(){
  return {
    databaseSecret:Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
    llm:Boolean(process.env.DEEPSEEK_API_KEY||process.env.OPENROUTER_API_KEY),
    auth:Boolean(process.env.ORCHESTRATOR_SECRET),
    realToolAdapters:false
  };
}

function authorized(req){
  const secret=process.env.ORCHESTRATOR_SECRET;
  if(!secret) return {ok:false,status:503,error:'orchestrator_secret_not_configured'};
  const auth=req.headers.get('authorization')||'';
  const supplied=auth.startsWith('Bearer ')?auth.slice(7):'';
  if(!supplied) return {ok:false,status:401,error:'unauthorized'};
  const a=Buffer.from(supplied),b=Buffer.from(secret);
  if(a.length!==b.length||!timingSafeEqual(a,b)) return {ok:false,status:401,error:'unauthorized'};
  return {ok:true};
}

export async function GET(){
  const config=staticConfig();
  const persistence=await persistenceHealth();
  const supervisedReady=persistence.ok&&config.llm&&config.auth;
  return NextResponse.json({
    service:'SocialMarket Autonomous Commerce OS',
    status:supervisedReady?'supervised-beta':'degraded',
    fullAutonomy:false,
    dependencies:{...config,persistence},
    limits:{maxPromptChars:MAX_PROMPT_CHARS,maxDurationSeconds:30},
    registry:getSiteRegistry()
  });
}

export async function POST(req){
  const auth=authorized(req);
  if(!auth.ok) return NextResponse.json({error:auth.error},{status:auth.status});
  try{
    const body=await req.json();
    const prompt=typeof body?.prompt==='string'?body.prompt.trim():'';
    if(!prompt) return NextResponse.json({error:'prompt_required'},{status:400});
    if(prompt.length>MAX_PROMPT_CHARS) return NextResponse.json({error:'prompt_too_large',maxPromptChars:MAX_PROMPT_CHARS},{status:413});

    const run=await orchestrate({
      prompt,
      approvedCapabilities:Array.isArray(body?.approvedCapabilities)?body.approvedCapabilities.slice(0,20):[]
    });
    const status=run.state==='WAITING_APPROVAL'?202:run.state==='FAILED'?500:200;
    return NextResponse.json(run,{status});
  }catch(e){
    return NextResponse.json({error:String(e)},{status:400});
  }
}
