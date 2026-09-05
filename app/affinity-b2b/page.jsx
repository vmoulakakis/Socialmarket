import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { affinityProducts } from './data';

export const metadata = {
  title: 'AFFINITY B2B Pain-Gap Products',
  description: 'Five evidence-first B2B affiliate opportunities for Greece/EU.',
};

export default async function AffinityHub() {
  const ids = affinityProducts.map((p) => p.aliexpressId);
  const { data } = await supabase.from('Product').select('aliexpressId,salePrice,commissionRate,mainImage,shopName').in('aliexpressId', ids);
  const records = Object.fromEntries((data || []).map((r) => [r.aliexpressId, r]));
  return <main style={{minHeight:'100vh',background:'#07111f',color:'#f7fbff',fontFamily:'Inter,system-ui,sans-serif',padding:'70px 24px'}}>
    <div style={{maxWidth:1180,margin:'0 auto'}}>
      <div style={{fontSize:12,letterSpacing:'.22em',fontWeight:900,color:'#ff6a00'}}>AFFINITY • B2B PAIN-GAP ENGINE</div>
      <h1 style={{fontSize:'clamp(48px,7vw,82px)',lineHeight:.95,letterSpacing:'-.055em',margin:'18px 0'}}>5 pages. 5 διαφορετικά pain gaps. Ένα conversion system.</h1>
      <p style={{maxWidth:760,fontSize:19,lineHeight:1.6,color:'#9db0c4'}}>Κάθε σελίδα χρησιμοποιεί το πραγματικό affiliate promotion link της SocialMarket βάσης και διαφορετικό positioning για τον αντίστοιχο B2B buyer.</p>
      <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:18,marginTop:44}}>
        {affinityProducts.map((p,i)=>{const r=records[p.aliexpressId]||{}; const price=Number(r.salePrice||0); const rate=parseFloat(String(r.commissionRate||'0'))||0; const commission=price*rate/100; return <Link key={p.slug} href={`/affinity-b2b/${p.slug}`} style={{textDecoration:'none',color:'inherit',border:'1px solid rgba(255,255,255,.09)',borderRadius:24,background:'linear-gradient(145deg,rgba(255,255,255,.06),rgba(255,255,255,.018))',overflow:'hidden',display:'block'}}>
          <div style={{height:220,display:'grid',placeItems:'center',background:`radial-gradient(circle at center,${p.accent}22,transparent 65%)`}}>{r.mainImage?<img src={r.mainImage} alt={p.shortName} style={{maxWidth:'80%',maxHeight:190,objectFit:'contain',filter:'drop-shadow(0 24px 30px #0008)'}}/>:null}</div>
          <div style={{padding:24}}><div style={{fontSize:12,fontWeight:900,color:p.accent}}>0{i+1} • {p.eyebrow}</div><h2 style={{fontSize:25,lineHeight:1.08,margin:'12px 0'}}>{p.shortName}</h2><p style={{color:'#8fa3b8',lineHeight:1.5,minHeight:72}}>{p.pain}</p><div style={{display:'flex',justifyContent:'space-between',alignItems:'end',borderTop:'1px solid rgba(255,255,255,.08)',paddingTop:18,marginTop:18}}><div><small style={{display:'block',color:'#73879b'}}>DB price</small><strong style={{fontSize:24}}>€{price.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}</strong></div><div style={{textAlign:'right'}}><small style={{display:'block',color:'#73879b'}}>theoretical commission</small><strong style={{color:p.accent}}>~€{commission.toFixed(2)}</strong></div></div></div>
        </Link>})}
      </section>
      <p style={{marginTop:36,fontSize:12,color:'#687d92'}}>Οι προμήθειες προκύπτουν μαθηματικά από την τιμή και το commissionRate της raw SocialMarket εγγραφής και δεν αποτελούν εγγυημένο payable affiliate payout. Η τελική αγορά γίνεται στον merchant.</p>
    </div>
  </main>;
}
