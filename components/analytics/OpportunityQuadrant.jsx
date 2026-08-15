'use client';

const clamp=v=>Math.max(0,Math.min(100,Number(v||0)));

export default function OpportunityQuadrant({items=[],labelKey='canonical_title',max=18}){
 const rows=(items||[]).filter(x=>x&&x.greek_demand_score!==null&&x.competition_score!==null).slice(0,max);
 return <div style={{width:'100%',overflow:'hidden'}}>
  <svg viewBox="0 0 720 390" role="img" aria-label="Demand versus competition opportunity quadrant" style={{width:'100%',height:'auto',display:'block'}}>
   <rect x="70" y="20" width="620" height="320" rx="14" fill="transparent" stroke="currentColor" opacity=".18"/>
   <line x1="380" y1="20" x2="380" y2="340" stroke="currentColor" opacity=".13" strokeDasharray="5 6"/>
   <line x1="70" y1="180" x2="690" y2="180" stroke="currentColor" opacity=".13" strokeDasharray="5 6"/>
   <text x="82" y="42" fontSize="12" opacity=".65">High demand / Low competition</text>
   <text x="500" y="42" fontSize="12" opacity=".5">High demand / High competition</text>
   <text x="82" y="329" fontSize="12" opacity=".5">Low demand / Low competition</text>
   <text x="492" y="329" fontSize="12" opacity=".5">Low demand / High competition</text>
   <text x="355" y="375" fontSize="12" opacity=".65">Competition →</text>
   <text x="18" y="194" fontSize="12" opacity=".65" transform="rotate(-90 18 194)">Demand →</text>
   {rows.map((x,i)=>{const demand=clamp(x.greek_demand_score),comp=clamp(x.competition_score),pain=clamp(x.pain_gap_fit_score);const cx=70+comp*6.2,cy=340-demand*3.2,r=5+pain*.085;const label=String(x[labelKey]||x.merchant_name||`#${i+1}`).slice(0,24);return <g key={x.product_id||x.merchant_id||i}><circle cx={cx} cy={cy} r={r} fill="currentColor" opacity={.25+clamp(x.product_evidence_confidence||60)/250}/><circle cx={cx} cy={cy} r="3" fill="currentColor"/><text x={Math.min(620,cx+r+4)} y={cy+4} fontSize="10" opacity=".8">{label}</text></g>})}
   {!rows.length&&<text x="245" y="190" fontSize="15" opacity=".5">No validated product points yet</text>}
  </svg>
 </div>
}
