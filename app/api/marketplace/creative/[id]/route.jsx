import {NextResponse} from 'next/server';
export async function GET(){return NextResponse.json({error:'creative_not_available',message:'No public creative asset has been approved for this catalog product.'},{status:404});}
