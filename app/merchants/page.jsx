'use client';
import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';

const score=v=>v==null?'—':Number(v).toFixed(1);
const confidence=v=>v==null?'—':`${Math.round(Number(v)<=1?Number(v)*100:Number(v))}%`;

export default function Merchants(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 useEffect(()=>{(async()=>{
   const {data,error}=await supabase.from('merchant_dashboard')
     .select('merchant_id,canonical_name,official_domain,primary_category,peer_group,trust_score,overall_opportunity_score,competition_intensity_score,greek_market_fit_score,deep_research_score,research_confidence,risk_flag,risk_reason,evidence_count,researched_at,global_rank,score_stage')
     .order('global_rank',{ascending:true,nullsFirst:false}).limit(309);
   setRows(data||[]);setError(error?.message||'');setLoading(false);
 })()},[]);
 return <main>
   <div className="hero"><div><div className="eyebrow">Evidence-first merchant selection</div><h1>Merchant Intelligence</h1><p className="sub">Canonical merchant research, trust, Greek-market fit, competition and opportunity. Missing metrics stay unknown instead of becoming fake zeros.</p></div></div>
   <div className="card">
     {loading?<p className="muted">Loading merchant intelligence…</p>:error?<p className="bad">Merchant data error: {error}</p>:rows.length===0?<p className="muted">Δεν υπάρχουν ακόμη canonical merchant rankings.</p>:
     <table className="table"><thead><tr><th>Rank</th><th>Merchant</th><th>Category</th><th>Trust</th><th>Opportunity</th><th>Greek fit</th><th>Competition</th><th>Deep research</th><th>Confidence</th><th>Evidence</th><th>Risk</th></tr></thead><tbody>
       {rows.map(m=><tr key={m.merchant_id}>
         <td>{m.global_rank??'—'}</td>
         <td><strong>{m.canonical_name}</strong><div className="muted">{m.official_domain||'domain unknown'}</div></td>
         <td>{m.primary_category||'—'}<div className="muted">{m.peer_group||''}</div></td>
         <td>{score(m.trust_score)}</td>
         <td className={Number(m.overall_opportunity_score)>=70?'score good':m.overall_opportunity_score==null?'':'score warn'}>{score(m.overall_opportunity_score)}</td>
         <td>{score(m.greek_market_fit_score)}</td>
         <td>{score(m.competition_intensity_score)}</td>
         <td>{score(m.deep_research_score)}</td>
         <td>{confidence(m.research_confidence)}</td>
         <td>{m.evidence_count??'—'}</td>
         <td>{m.risk_flag?<span className="pill bad" title={m.risk_reason||''}>RISK</span>:<span className="pill">OK</span>}</td>
       </tr>)}
     </tbody></table>}
     <p className="muted" style={{marginTop:14}}>Scores are evidence-backed intelligence fields. Unknown values remain “—”; they are not interpreted as zero.</p>
   </div>
 </main>
}
