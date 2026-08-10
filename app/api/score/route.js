import {NextResponse} from 'next/server';import {calculateHigo} from '@/lib/higo';
export async function POST(req){try{return NextResponse.json(calculateHigo(await req.json()))}catch(e){return NextResponse.json({error:String(e)},{status:400})}}
