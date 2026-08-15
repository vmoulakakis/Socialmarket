'use client';

const clamp=v=>Math.max(0,Math.min(100,Number(v||0)));
const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));

export default function CategoryMarketScatter({items=[],max=24}){
 const rows=(items||[]).filter(x=>valid(x.demand_score)&&valid(x.competition_score)).slice(0,max);
 return <svg viewBox="0 0 760 400" role="img" aria-label="Canonical category demand versus competition" style={{width:'100%',height:'auto',display:'block'}}>
  <rect x="70" y="20" width="650" height="320" rx="14" fill="transparent" stroke="currentColor" opacity=".16"/>
  <line x1="395" y1="20" x2="395" y2="340" stroke="currentColor" opacity=".12" strokeDasharray="5 6"/>
  <line x1="70" y1="180" x2="720" y2="180" stroke="currentColor" opacity=".12" strokeDasharray="5 6"/>
  <text x="84" y="42" fontSize="12" opacity=".7">Priority whitespace</text><text x="555" y="42" fontSize="12" opacity=".5">High demand / crowded</text>
  <text x="84" y="330" fontSize="12" opacity=".5">Low evidence demand</text><text x="555" y="330" fontSize="12" opacity=".5">Avoid / validate</text>
  <text x="350" y="382" fontSize="12" opacity=".65">Competition →</text><text x="18" y="200" fontSize="12" opacity=".65" transform="rotate(-90 18 200)">Demand →</text>
  {rows.map((x,i)=>{const d=clamp(x.demand_score),c=clamp(x.competition_score),p=clamp(x.pain_gap_score),cx=70+c*6.5,cy=340-d*3.2,r=5+p*.08,label=String(x.subcategory_name||x.taxonomy_name||x.category_name||`#${i+1}`).slice(0,24);return <g key={x.id||i}><circle cx={cx} cy={cy} r={r} fill="currentColor" opacity=".34"/><circle cx={cx} cy={cy} r="2.8" fill="currentColor"/><text x={Math.min(625,cx+r+4)} y={cy+4} fontSize="9.5" opacity=".8">{label}</text></g>})}
  {!rows.length&&<text x="235" y="188" fontSize="14" opacity=".5">Competition evidence not yet sufficient for plotting</text>}
 </svg>
}
