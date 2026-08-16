'use client';
import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';

const score=v=>v==null?'—':Number(v).toFixed(1);
const confidence=v=>v==null?'—':`${Math.round(Number(v)<=1?Number(v)*100:Number(v))}%`;

export default function Niches(){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
 useEffect(()=>{(async()=>{
   const {data,error}=await supabase.from('category_market_dashboard')
     .select('id,taxonomy_id,category_name,subcategory_name,taxonomy_name,node_type,observed_at,demand_score,competition_score,pain_gap_score,satisfaction_score,opportunity_score,confidence,validated_pain_clusters,methodology_version')
     .order('opportunity_score',{ascending:false,nullsFirst:false}).limit(500);
   setRows(data||[]);setError(error?.message||'');setLoading(false);
 })()},[]);
 return <main>
   <div className="hero"><div><div className="eyebrow">Semantic Category Market</div><h1>Market & Pain Intelligence</h1><p className="sub">Greek taxonomy-level demand, competition, pain-gap and opportunity signals. Forecasts are not shown as facts when the temporal model is withheld.</p></div></div>
   <div className="card">
     {loading?<p className="muted">Loading category market intelligence…</p>:error?<p className="bad">Category market error: {error}</p>:rows.length===0?<p className="muted">Δεν υπάρχουν ακόμη category-market observations.</p>:
     <table className="table"><thead><tr><th>Category / Market</th><th>Demand</th><th>Competition</th><th>Pain gap</th><th>Satisfaction</th><th>Opportunity</th><th>Confidence</th><th>Validated pains</th><th>Observed</th></tr></thead><tbody>
       {rows.map(n=><tr key={n.id}>
         <td><strong>{n.subcategory_name||n.taxonomy_name||n.category_name}</strong><div className="muted">{n.category_name}{n.node_type?` · ${n.node_type}`:''}</div></td>
         <td>{score(n.demand_score)}</td>
         <td>{score(n.competition_score)}</td>
         <td>{score(n.pain_gap_score)}</td>
         <td>{score(n.satisfaction_score)}</td>
         <td className={Number(n.opportunity_score)>=70?'score good':n.opportunity_score==null?'':'score warn'}>{score(n.opportunity_score)}</td>
         <td>{confidence(n.confidence)}</td>
         <td>{n.validated_pain_clusters??0}</td>
         <td>{n.observed_at?new Date(n.observed_at).toLocaleDateString('el-GR'):'—'}</td>
       </tr>)}
     </tbody></table>}
     <p className="muted" style={{marginTop:14}}>Competition and other missing metrics remain “—”. Zero is displayed only when zero is actually stored.</p>
   </div>
 </main>
}
