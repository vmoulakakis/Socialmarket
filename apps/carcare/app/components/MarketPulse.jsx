"use client";
import {useState,useEffect} from "react";
const groups=[["visibility","Ορατότητα"],["lighting","Φώτα"],["cleaning","Καθαρισμός"],["electrical","Ηλεκτρικά"],["gadgets","Gadgets"],["maintenance","Συντήρηση"]];
export default function MarketPulse(){
 const [counts,setCounts]=useState(null);
 useEffect(()=>{fetch("/api/catalog?problem=visibility").then(r=>r.json()).then(d=>setCounts(d.problem_counts||null)).catch(()=>{})},[]);
 const max=counts?Math.max(1,...Object.values(counts).map(Number)):1;
 return <section className="marketPulse"><h2>Προϊόντα ανά ανάγκη</h2><p>Μόνο μετρήσεις του καταλόγου, όχι εκτιμήσεις ζήτησης.</p><div className="pulseGrid">{groups.map(([k,name])=><a href="#advisor" className="pulseItem" key={k}><strong>{name}</strong><b>{counts?Number(counts[k]||0).toLocaleString("el-GR"):"—"}</b><span className="pulseTrack"><span style={{width:counts?(100*Number(counts[k]||0)/max)+"%":"0%"}}/></span></a>)}</div></section>
}
