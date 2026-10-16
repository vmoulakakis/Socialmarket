'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {workspace} from '@/lib/workspace-client';
const stages=[['Demand','/demand','problem_demand_assessed'],['Merchants','/merchants','eligible_merchants'],['Product offers','/products','eligible_product_offers'],['Final AI selection','/forecast-products','selected_products'],['Creative briefs','/creatives','approved_social_presentations'],['Publishing outbox','/scheduler','publishing_jobs_open']];
export default function ControlTower(){
 const [data,setData]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 async function load(){setLoading(true);setError('');try{setData(await workspace());}catch(e){setError(e.message);setData(null);}finally{setLoading(false);}}
 useEffect(()=>{void load();},[]);
 const health=data?.health,c=health?.counts||{};
 return <main className="semanticConsole">
 <header className="semanticHero"><div><span>PRODUCTION · CANONICAL DATA</span><h1>SocialMarket Control Tower</h1><p>Demand → Merchant verification → Product evaluation → Creative briefs → Approved publishing intent.</p></div><button onClick={load} disabled={loading}>↻ Ανανέωση</button></header>
 {loading&&<p role="status">Φόρτωση κατάστασης…</p>}{error&&<p role="alert" className="semanticError">{error}</p>}
 {health&&<><section className="semanticPanel"><div className="semanticPanelHead"><h2>Pipeline: {health.pipeline_status.replaceAll('_',' ')}</h2><span className={health.pipeline_status==='operational'?'semanticGood':'semanticWarn'}>{health.pipeline_status==='operational'?'OPERATIONAL':'NEEDS ATTENTION'}</span></div><p>Επόμενη ενέργεια: <b>{health.next_action.replaceAll('_',' ')}</b></p><p>{c.merchant360_assessed} / {c.active_merchants} merchants έχουν αξιολόγηση. {c.merchant_program_or_tracking_unverified} χρειάζονται επαλήθευση program/tracking. {c.selected_products} προϊόντα έχουν περάσει στην τελική επιλογή.</p><Link href="/admin">Έλεγχος πολιτικών και ρυθμίσεων →</Link></section>
 <section className="semanticGrid2">{stages.map(([title,href,key],i)=><article className="semanticPanel" key={href}><div className="semanticPanelHead"><div><span>STAGE {i+1}</span><h2>{title}</h2></div><strong>{c[key]??'—'}</strong></div><p>{key==='eligible_product_offers'?'Εισαγμένα offers πριν από την τελική επιλογή AI.':key==='publishing_jobs_open'?'Αποθηκευμένα jobs. Η πραγματική δημοσίευση επιβεβαιώνεται μόνο από το external post status.':key==='selected_products'?'Μόνο το αποτέλεσμα του canonical selection, χωρίς συμπλήρωση με μη αξιολογημένα offers.':'Πραγματικές εγγραφές από τη VMDB.'}</p><Link href={href}>Άνοιγμα {title} →</Link></article>)}</section>
 <section className="semanticPanel"><h2>Τι χρειάζεται για πλήρη λειτουργία</h2><p>Ολοκλήρωση merchant research και επαλήθευση affiliate program/tracking, product evaluation και skeptic audit. Τα παλιά research workflows παραμένουν manual-only επειδή χρησιμοποιούσαν το διαγραμμένο legacy project.</p><p>Semantic embeddings: {c.semantic_embeddings_ready} ready / {c.semantic_embeddings_pending} pending · Performance feedback: {c.performance_feedback_events} events.</p><Link href="/analytics">Ιστορικό πραγματικών εκτελέσεων →</Link></section></>}
 <footer className="semanticFooter">{data?.generated_at?new Date(data.generated_at).toLocaleString('el-GR'):'—'} · Missing ≠ zero · Imported offers ≠ AI-selected products</footer>
 </main>;
}
