import {createClient} from '@supabase/supabase-js';
import {APPROVED_ADMIN_EMAIL,APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';
export async function adminAuth(req){
 const auth=req.headers.get('authorization')||'';
 const token=auth.startsWith('Bearer ')?auth.slice(7):'';
 if(!token)return null;
 try{
  const client=createClient(APPROVED_SUPABASE_URL,APPROVED_PUBLISHABLE_KEY,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data,error}=await client.auth.getUser(token);
  if(error||String(data?.user?.email||'').toLowerCase()!==APPROVED_ADMIN_EMAIL)return null;
  return {accessToken:token,userId:data.user.id};
 }catch{return null;}
}
