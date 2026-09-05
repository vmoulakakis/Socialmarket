import {ImageResponse} from 'next/og';
import {APPROVED_PUBLISHABLE_KEY,APPROVED_SUPABASE_URL} from '@/lib/supabase-config';

export const runtime='edge';

const presets={
  feed:{width:1080,height:1350,label:'FEED 4:5'},
  story:{width:1080,height:1920,label:'STORY 9:16'},
  square:{width:1080,height:1080,label:'SQUARE 1:1'},
};
const safe=v=>String(v||'').trim();
const short=(v,n)=>safe(v).slice(0,n);

async function getItem(id){
 const url=`${APPROVED_SUPABASE_URL}/rest/v1/socialmarket_marketplace200_public_v?id=eq.${encodeURIComponent(id)}&select=*`;
 const r=await fetch(url,{headers:{apikey:APPROVED_PUBLISHABLE_KEY,Authorization:`Bearer ${APPROVED_PUBLISHABLE_KEY}`},next:{revalidate:300}});
 if(!r.ok)return null;const rows=await r.json();return rows?.[0]||null;
}

export async function GET(request,{params}){
 const {id}=await params;const item=await getItem(decodeURIComponent(String(id||'')));
 if(!item)return new Response('Case not found',{status:404});
 const q=new URL(request.url).searchParams;const key=q.get('format')||'feed';const preset=presets[key]||presets.feed;
 const target=safe(item.tracking_url);const image=safe(item.image_url);const social=item.social_copy&&typeof item.social_copy==='object'?item.social_copy:{};
 const hook=short(social.hook||item.solution_statement||item.job_to_be_done,170);
 const pain=short(item.pain_statement,150);const niche=short(item.subniche||item.niche||'PROBLEM SOLVER',60);
 const qr=target?`https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=14&data=${encodeURIComponent(target)}`:'';
 const compact=preset.height<=1080;const vertical=preset.height>=1800;
 return new ImageResponse(
  <div style={{width:'100%',height:'100%',display:'flex',position:'relative',background:'#111318',color:'#fff',fontFamily:'Arial, Helvetica, sans-serif',overflow:'hidden'}}>
   {image&&<img src={image} alt="" style={{position:'absolute',width:'100%',height:'100%',objectFit:'cover'}}/>}
   <div style={{position:'absolute',inset:0,display:'flex',background:'linear-gradient(180deg, rgba(17,19,24,.08) 15%, rgba(17,19,24,.38) 45%, rgba(17,19,24,.96) 100%)'}}/>
   <div style={{position:'absolute',top:compact?44:62,left:compact?44:58,right:compact?44:58,display:'flex',alignItems:'center',justifyContent:'space-between'}}>
    <div style={{display:'flex',alignItems:'center',gap:14}}><div style={{width:58,height:58,borderRadius:18,background:'#111318',color:'#ddff55',display:'flex',alignItems:'center',justifyContent:'center',fontSize:30,fontWeight:900}}>S</div><div style={{display:'flex',flexDirection:'column'}}><span style={{fontSize:22,fontWeight:900}}>SocialMarket</span><span style={{fontSize:11,letterSpacing:3,opacity:.72}}>FIND WHAT FIXES IT</span></div></div>
    <div style={{background:'#ddff55',color:'#111318',padding:'12px 18px',borderRadius:999,fontSize:13,fontWeight:900,letterSpacing:2}}>{preset.label}</div>
   </div>
   <div style={{position:'absolute',left:compact?44:58,right:compact?44:58,bottom:compact?42:60,display:'flex',flexDirection:vertical?'column':'row',alignItems:vertical?'stretch':'flex-end',justifyContent:'space-between',gap:vertical?30:36}}>
    <div style={{display:'flex',flexDirection:'column',maxWidth:vertical?'100%':'74%'}}>
     <span style={{fontSize:vertical?16:13,fontWeight:900,letterSpacing:3,color:'#ddff55',textTransform:'uppercase'}}>{niche}</span>
     <div style={{fontSize:vertical?82:compact?56:64,lineHeight:.95,fontWeight:900,letterSpacing:-3,marginTop:18}}>{short(item.product_name,vertical?110:92)}</div>
     <div style={{fontSize:vertical?30:22,lineHeight:1.22,fontWeight:700,marginTop:24,maxWidth:880}}>{hook}</div>
     {!compact&&<div style={{display:'flex',marginTop:22,paddingTop:18,borderTop:'1px solid rgba(255,255,255,.35)',fontSize:16,lineHeight:1.35,opacity:.82}}><span style={{color:'#ff6b47',fontWeight:900,marginRight:12}}>PAIN →</span>{pain}</div>}
    </div>
    {qr&&<div style={{display:'flex',flexDirection:'column',alignItems:'center',background:'#f4efe6',color:'#111318',padding:14,borderRadius:24,minWidth:vertical?250:210}}><img src={qr} alt="" width={vertical?220:180} height={vertical?220:180} style={{borderRadius:12}}/><span style={{fontSize:11,fontWeight:900,letterSpacing:1.5,marginTop:8}}>SCAN TO CHECK</span></div>}
   </div>
   <div style={{position:'absolute',right:compact?36:48,top:vertical?280:210,width:vertical?170:145,height:vertical?170:145,borderRadius:999,background:'#ff6b47',display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',fontSize:vertical?25:21,fontWeight:900,lineHeight:.9,transform:'rotate(8deg)',boxShadow:'0 20px 50px rgba(0,0,0,.2)'}}>PAIN<br/>→ FIX</div>
  </div>,
  {width:preset.width,height:preset.height,headers:{'Cache-Control':'public, max-age=300, s-maxage=300'}}
 );
}
