import {NextResponse} from 'next/server';
import {orchestrate,getSiteRegistry} from '@/lib/orchestrator/runtime';

export async function GET(){
  return NextResponse.json({
    service:'SocialMarket Autonomous Commerce OS',
    status:'ready',
    registry:getSiteRegistry()
  });
}

export async function POST(req){
  try{
    const body=await req.json();
    const run=await orchestrate({
      prompt:body?.prompt,
      approvedCapabilities:Array.isArray(body?.approvedCapabilities)?body.approvedCapabilities:[]
    });
    const status=run.state==='WAITING_APPROVAL'?202:run.state==='FAILED'?500:200;
    return NextResponse.json(run,{status});
  }catch(e){
    return NextResponse.json({error:String(e)},{status:400});
  }
}
