import {NextResponse} from 'next/server';
import {agentCompletion} from '@/lib/model-router';
import {adminAuth} from '@/lib/admin-auth';
export const maxDuration=60;
export async function POST(req){
 const auth=await adminAuth(req);
 if(!auth)return NextResponse.json({error:'admin_session_required'},{status:401});
 let body;try{body=await req.json();}catch{return NextResponse.json({error:'invalid_json'},{status:400});}
 if(typeof body?.question!=='string'||!body.question.trim()||body.question.length>6000)return NextResponse.json({error:'valid_question_required'},{status:400});
 try{return NextResponse.json(await agentCompletion({accessToken:auth.accessToken,json:true,messages:[{role:'system',content:'You are the Greek Market Opportunity Analyst. Never invent demand. Separate evidence, inference and unknowns. Return JSON.'},{role:'user',content:JSON.stringify({question:body.question,context:body.context})}]}));}
 catch{return NextResponse.json({error:'ai_provider_unavailable'},{status:503});}
}
