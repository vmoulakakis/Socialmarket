import Link from 'next/link';
import { affinityProducts } from './data';
import { affiliateRecords as productRecords } from './records';

export const metadata = {
  title: 'AFFINITY B2B Smart Buying',
  description: 'Five B2B sourcing opportunities focused on total cost, margin and due diligence.',
};

export default function AffinityHub(){
  return <main style={{minHeight:'100vh',background:'#06101b',color:'#f5f8fc',fontFamily:'Inter,system-ui,sans-serif',padding:'70px 24px'}}>
    <div style={{maxWidth:1180,margin:'0 auto'}}>
      <div style={{fontSize:12,letterSpacing:'.22em',fontWeight:900,color:'#ff8a32'}}>AFFINITY • SMART B2B BUYING</div>
      <h1 style={{fontSize:'clamp(46px,7vw,82px)',lineHeight:.95,letterSpacing:'-.055em',margin:'18px 0'}}>Αγοράζεις σαν έμπορος. Μετράς κόστος. Προστατεύεις το κέρδος.</h1>
      <p style={{maxWidth:820,fontSize:19,lineHeight:1.65,color:'#9db0c4'}}>Πέντε επαγγελματικές λύσεις με διαφορετικό pain gap. Η λογική είναι κοινή: σύγκρινε landed cost, τεχνικό fit, seller risk, warranty και πραγματικό εμπορικό όφελος πριν αγοράσεις.</p>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginTop:30}}>
        {['Κόστος αγοράς','Κόστος λειτουργίας','Περιθώριο κέρδους'].map((x,i)=><div key={x} style={{padding:18,border:'1px solid #ffffff12',borderRadius:16,background:'#ffffff06'}}><small style={{color:'#71859a'}}>0{i+1}</small><strong style={{display:'block',fontSize:18,marginTop:6}}>{x}</strong></div>)}
      </div>
      <section style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:18,marginTop:42}}>
        {affinityProducts.map((p,i)=>{const r=productRecords[p.aliexpressId]||{};const price=Number(r.salePrice||0);return <Link key={p.slug} href={`/affinity-b2b/${p.slug}`} style={{textDecoration:'none',color:'inherit',border:'1px solid #ffffff12',borderRadius:24,background:'linear-gradient(145deg,#ffffff09,#ffffff03)',overflow:'hidden',display:'block'}}>
          <div style={{height:220,display:'grid',placeItems:'center',background:`radial-gradient(circle at center,${p.accent}22,transparent 65%)`}}>{r.mainImage?<img src={r.mainImage} alt={p.shortName} style={{maxWidth:'80%',maxHeight:190,objectFit:'contain',filter:'drop-shadow(0 24px 30px #0008)'}}/>:null}</div>
          <div style={{padding:24}}><div style={{fontSize:12,fontWeight:900,color:p.accent}}>0{i+1} • {p.eyebrow}</div><h2 style={{fontSize:25,lineHeight:1.08,margin:'12px 0'}}>{p.shortName}</h2><p style={{color:'#8fa3b8',lineHeight:1.5,minHeight:72}}>{p.pain}</p><div style={{borderTop:'1px solid #ffffff12',paddingTop:18,marginTop:18}}><small style={{display:'block',color:'#73879b'}}>Τιμή snapshot</small><strong style={{fontSize:25}}>€{price.toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}</strong><span style={{display:'block',color:'#91a4b6',fontSize:12,marginTop:8}}>Άνοιξε τη σελίδα για landed-cost calculator και B2B due diligence →</span></div></div>
        </Link>})}
      </section>
      <div style={{marginTop:38,padding:22,borderRadius:18,border:'1px solid #ffffff12',background:'#ffffff05',color:'#8fa3b8',lineHeight:1.6,fontSize:13}}>Οι εμφανιζόμενες τιμές είναι snapshots και όχι υπόσχεση τελικής τιμής. Δεν παρουσιάζουμε seller ως «ευρωπαϊκό» ή «πιστοποιημένο» χωρίς επαλήθευση. Ο αγοραστής πρέπει να επιβεβαιώνει Ship From, ΦΠΑ/δασμούς, warranty, returns, ακριβές configuration και τελικό landed cost πριν την πληρωμή.</div>
    </div>
  </main>
}
