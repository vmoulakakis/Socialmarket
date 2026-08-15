'use client';

import {useEffect,useMemo,useState} from 'react';
import {motion} from 'motion/react';
import {flexRender,getCoreRowModel,getSortedRowModel,useReactTable} from '@tanstack/react-table';
import {supabase} from '@/lib/supabase';
import EChart from '@/components/analytics/EChart';
import styles from './demand.module.css';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const num=v=>valid(v)?Number(v):null;
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
const pct=v=>valid(v)?`${fmt(Number(v)*100,0)}%`:'—';
const label=x=>x.subcategory_name||x.category_name||x.taxonomy_name||'Unclassified';
const palette={text:'#e9eef7',muted:'#7f8ba0',line:'rgba(148,163,184,.16)',violet:'#8b5cf6',cyan:'#22d3ee',emerald:'#34d399',amber:'#fbbf24',red:'#fb7185'};

function Stat({label,value,meta,tone='violet'}){return <div className={styles.stat}><span>{label}</span><strong data-tone={tone}>{value}</strong><small>{meta}</small></div>}
function EmptyVisual({title,children,code}){return <div className={styles.emptyVisual}>{code&&<span>{code}</span>}<b>{title}</b><p>{children}</p></div>}
function Panel({eyebrow,title,aside,children,className=''}){return <section className={`${styles.panel} ${className}`}><header className={styles.panelHead}><div><span>{eyebrow}</span><h2>{title}</h2></div>{aside}</header>{children}</section>}

export default function DemandIntelligence(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [category,setCategory]=useState('All'),[sorting,setSorting]=useState([]),[aiBusy,setAiBusy]=useState(false),[ai,setAi]=useState(null);
 async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_dashboard_snapshot');if(error)setError(error.message);else setData(data);setLoading(false)}
 useEffect(()=>{load()},[]);
 const allRows=useMemo(()=>[...(data?.category_market||[])], [data]);
 const categoryNames=useMemo(()=>['All',...Array.from(new Set(allRows.map(x=>x.category_name||x.taxonomy_name).filter(Boolean))).sort()], [allRows]);
 const rows=useMemo(()=>allRows.filter(x=>category==='All'||(x.category_name||x.taxonomy_name)===category),[allRows,category]);
 const comparable=useMemo(()=>rows.filter(x=>valid(x.demand_score)&&valid(x.competition_score)),[rows]);
 const ranked=useMemo(()=>[...comparable].filter(x=>valid(x.opportunity_score)).sort((a,b)=>Number(b.opportunity_score)-Number(a.opportunity_score)),[comparable]);
 const top=ranked[0]||null;
 const missingCompetition=rows.filter(x=>!valid(x.competition_score)).length;
 const avgConfidence=rows.filter(x=>valid(x.confidence)).length?rows.filter(x=>valid(x.confidence)).reduce((s,x)=>s+Number(x.confidence),0)/rows.filter(x=>valid(x.confidence)).length:null;
 const evidenceTotal=rows.reduce((s,x)=>s+Number(x.evidence_entities||0),0);
 const painRows=data?.pain_gaps||[];

 const scatter=useMemo(()=>({
  backgroundColor:'transparent',animationDuration:650,textStyle:{color:palette.text,fontFamily:'Inter,system-ui,sans-serif'},
  grid:{left:52,right:28,top:34,bottom:54},
  xAxis:{name:'Competition →',min:0,max:100,nameLocation:'middle',nameGap:34,axisLine:{lineStyle:{color:palette.line}},axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.08)'}}},
  yAxis:{name:'Demand →',min:0,max:100,nameLocation:'middle',nameGap:40,axisLine:{lineStyle:{color:palette.line}},axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.08)'}}},
  tooltip:{trigger:'item',backgroundColor:'#0b1220',borderColor:'rgba(148,163,184,.2)',textStyle:{color:palette.text},formatter:p=>{const v=p.value;return `<b>${v[5]}</b><br/>Demand ${fmt(v[1])}<br/>Competition ${fmt(v[0])}<br/>Opportunity ${fmt(v[3])}<br/>Evidence ${fmt(v[2])}<br/>Confidence ${valid(v[4])?fmt(v[4]*100)+'%':'—'}`}},
  visualMap:{show:false,min:0,max:100,dimension:3,inRange:{color:['#475569','#22d3ee','#8b5cf6','#34d399']}},
  series:[{type:'scatter',data:comparable.map(x=>[Number(x.competition_score),Number(x.demand_score),Number(x.evidence_entities||0),Number(x.opportunity_score||0),num(x.confidence),label(x)]),symbolSize:v=>Math.max(11,Math.min(42,11+Math.sqrt(Math.max(0,v[2]))*3)),itemStyle:{opacity:.8,borderColor:'rgba(255,255,255,.32)',borderWidth:1},emphasis:{scale:1.18,itemStyle:{opacity:1}},markArea:{silent:true,label:{color:'rgba(226,232,240,.5)',fontSize:10},itemStyle:{opacity:.045},data:[[{name:'WHITESPACE',xAxis:0,yAxis:50,itemStyle:{color:palette.emerald}},{xAxis:50,yAxis:100}],[{name:'CROWDED DEMAND',xAxis:50,yAxis:50,itemStyle:{color:palette.amber}},{xAxis:100,yAxis:100}],[{name:'EMERGING',xAxis:0,yAxis:0,itemStyle:{color:palette.cyan}},{xAxis:50,yAxis:50}],[{name:'VALIDATE',xAxis:50,yAxis:0,itemStyle:{color:palette.red}},{xAxis:100,yAxis:50}]]}}]
 }),[comparable]);

 const matrix=useMemo(()=>{
  const topRows=[...rows].filter(x=>valid(x.demand_score)).sort((a,b)=>Number(b.opportunity_score??b.demand_score)-Number(a.opportunity_score??a.demand_score)).slice(0,14);
  const dims=['Demand','Competition','Pain','Opportunity','Confidence'];
  const heat=[];topRows.forEach((x,y)=>{[x.demand_score,x.competition_score,x.pain_gap_score,x.opportunity_score,valid(x.confidence)?Number(x.confidence)*100:null].forEach((v,xi)=>{if(valid(v))heat.push([xi,y,Number(v)])})});
  return {topRows,dims,option:{backgroundColor:'transparent',animationDuration:500,textStyle:{color:palette.text,fontFamily:'Inter,system-ui,sans-serif'},grid:{left:145,right:26,top:18,bottom:38},xAxis:{type:'category',data:dims,axisLine:{lineStyle:{color:palette.line}},axisLabel:{color:palette.muted,fontSize:10}},yAxis:{type:'category',inverse:true,data:topRows.map(label),axisLine:{show:false},axisLabel:{color:'#aeb9ca',fontSize:10,width:125,overflow:'truncate'}},visualMap:{show:false,min:0,max:100,inRange:{color:['#111827','#164e63','#2563eb','#7c3aed','#34d399']}},tooltip:{position:'top',formatter:p=>`${topRows[p.value[1]]?label(topRows[p.value[1]]):''}<br/>${dims[p.value[0]]}: <b>${fmt(p.value[2])}</b>`},series:[{type:'heatmap',data:heat,itemStyle:{borderWidth:2,borderColor:'#090e17',borderRadius:4},emphasis:{itemStyle:{shadowBlur:16,shadowColor:'rgba(34,211,238,.18)'}}}]}};
 },[rows]);

 const treemap=useMemo(()=>({backgroundColor:'transparent',animationDuration:650,tooltip:{backgroundColor:'#0b1220',borderColor:'rgba(148,163,184,.2)',textStyle:{color:palette.text},formatter:p=>`${p.name}<br/>Evidence footprint: <b>${fmt(p.value)}</b>`},series:[{type:'treemap',roam:false,nodeClick:false,breadcrumb:{show:false},label:{show:true,color:'#f8fafc',fontSize:11,formatter:'{b}'},upperLabel:{show:true,height:24,color:'#cbd5e1',fontWeight:700},itemStyle:{borderColor:'#090e17',borderWidth:3,gapWidth:3},levels:[{itemStyle:{borderWidth:0,gapWidth:4}},{colorSaturation:[.25,.7],itemStyle:{borderWidth:2,gapWidth:2,borderColorSaturation:.7}}],data:Object.entries(rows.reduce((acc,x)=>{const cat=x.category_name||x.taxonomy_name||'Other';const value=Number(x.evidence_entities||0);if(value<=0)return acc;(acc[cat]??=[]).push({name:x.subcategory_name||'Category level',value});return acc},{})).map(([name,children])=>({name,value:children.reduce((s,x)=>s+x.value,0),children}))}]}),[rows]);

 const columns=useMemo(()=>[
  {accessorFn:r=>r.category_name||r.taxonomy_name||'—',id:'category',header:'Category',cell:i=>String(i.getValue()??'—')},
  {accessorFn:r=>r.subcategory_name||'Category level',id:'subcategory',header:'Subcategory',cell:i=>String(i.getValue()??'—')},
  {accessorKey:'demand_score',header:'Demand',cell:i=>fmt(i.getValue())},
  {accessorKey:'competition_score',header:'Competition',cell:i=>fmt(i.getValue())},
  {accessorKey:'pain_gap_score',header:'Pain',cell:i=>fmt(i.getValue())},
  {accessorKey:'opportunity_score',header:'Opportunity',cell:i=><b>{fmt(i.getValue())}</b>},
  {accessorKey:'confidence',header:'Confidence',cell:i=>pct(i.getValue())},
  {accessorKey:'evidence_entities',header:'Evidence',cell:i=>fmt(i.getValue())},
 ],[]);
 const table=useReactTable({data:rows,columns,state:{sorting},onSortingChange:setSorting,getCoreRowModel:getCoreRowModel(),getSortedRowModel:getSortedRowModel()});

 async function runAnalyst(){setAiBusy(true);setError('');try{const {data:{session}}=await supabase.auth.getSession();const r=await fetch('https://rpfadpdnnxequgvdcfoq.supabase.co/functions/v1/admin-intelligence-gateway',{method:'POST',headers:{'content-type':'application/json','authorization':`Bearer ${session?.access_token||''}`},body:JSON.stringify({action:'forecast',generated_at:data?.generated_at,category_market:rows,pain_gaps:painRows,merchants:data?.merchants||[],social:data?.social||[]})});const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||`HTTP ${r.status}`);setAi(j.forecast)}catch(e){setError(String(e.message||e))}finally{setAiBusy(false)}}

 if(loading)return <main className={styles.page}><div className={styles.loading}>Loading production demand intelligence…</div></main>;
 return <main className={styles.page}>
  <motion.header className={styles.hero} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:.35}}>
   <div className={styles.heroCopy}><span className={styles.kicker}>DEMAND INTELLIGENCE · PRODUCTION</span><h1>{top?<>Best comparable signal: <em>{label(top)}</em></>:<>Demand intelligence needs comparable market evidence</>}</h1><p>{top?`Observed demand ${fmt(top.demand_score)} · competition ${fmt(top.competition_score)} · opportunity ${fmt(top.opportunity_score)} · confidence ${pct(top.confidence)}. Scores are existing production metrics; this screen does not re-score them.`:'No synthetic trend, search volume or competition score is generated to fill gaps.'}</p></div>
   <div className={styles.heroActions}><select value={category} onChange={e=>setCategory(e.target.value)} aria-label="Filter category">{categoryNames.map(x=><option key={x}>{x}</option>)}</select><button onClick={load}>Refresh</button><button className={styles.primary} onClick={runAnalyst} disabled={aiBusy}>{aiBusy?'Analyzing…':'AI Explain Demand'}</button></div>
  </motion.header>
  {error&&<div className={styles.error}>{error}</div>}

  <section className={styles.stats}>
   <Stat label="Trusted market rows" value={fmt(rows.length)} meta={`${fmt(comparable.length)} comparable`} tone="cyan"/>
   <Stat label="Evidence footprint" value={fmt(evidenceTotal)} meta="row-level evidence entities" tone="violet"/>
   <Stat label="Competition missing" value={fmt(missingCompetition)} meta="kept missing, never zero" tone={missingCompetition?'amber':'emerald'}/>
   <Stat label="Average confidence" value={avgConfidence===null?'—':pct(avgConfidence)} meta="across rows that report confidence" tone="emerald"/>
   <Stat label="Validated pains" value={fmt(painRows.length)} meta="audit-gated unmet needs" tone="amber"/>
  </section>

  <Panel eyebrow="OPPORTUNITY LANDSCAPE" title="Demand × Competition" aside={<span className={styles.legend}>Bubble size = evidence footprint · color = existing opportunity score</span>} className={styles.heroPanel}>
   {comparable.length?<EChart option={scatter} height={500} ariaLabel="Demand versus competition opportunity landscape"/>:<EmptyVisual code="NO COMPARABLE ROWS" title="Competition evidence is still incomplete">Rows without both demand and competition are intentionally excluded from the quadrant.</EmptyVisual>}
  </Panel>

  <div className={styles.grid2}>
   <Panel eyebrow="SIGNAL MATRIX" title="What is driving the landscape" aside={<span className={styles.legend}>Existing 0–100 metrics only</span>}>
    {matrix.topRows.length?<EChart option={matrix.option} height={430} ariaLabel="Demand signal matrix heatmap"/>:<EmptyVisual title="No signal matrix yet">The semantic market run has not produced trusted demand rows.</EmptyVisual>}
   </Panel>
   <Panel eyebrow="EVIDENCE FOOTPRINT" title="Where market evidence concentrates" aside={<span className={styles.legend}>Area = evidence entities, not market size</span>}>
    {evidenceTotal>0?<EChart option={treemap} height={430} ariaLabel="Market evidence footprint treemap"/>:<EmptyVisual title="No evidence footprint yet">Evidence entity counts are not available for these market rows.</EmptyVisual>}
   </Panel>
  </div>

  <div className={styles.grid3}>
   <Panel eyebrow="TREND EXPLORER" title="7D · 30D · 90D">
    <EmptyVisual code="FAIL-CLOSED" title="Historical demand series is not exposed by the current snapshot">No decorative sparkline is rendered. When production history is exposed, this module will compare real periods.</EmptyVisual>
   </Panel>
   <Panel eyebrow="PAIN LANDSCAPE" title="Validated unmet needs">
    {painRows.length?<div className={styles.painList}>{painRows.slice(0,8).map(p=><div key={p.id}><span>{p.category||'Unclassified'}</span><b>{p.canonical_text}</b><small>Severity {fmt(p.pain_severity)} · {fmt(p.evidence_count)} evidence · {fmt(p.source_diversity)} sources</small></div>)}</div>:<EmptyVisual code="0 VALIDATED PAINS" title="The hardened audit is doing its job">Contaminated legacy pains remain excluded. Product promotion cannot use unvalidated need evidence.</EmptyVisual>}
   </Panel>
   <Panel eyebrow="LINEAGE" title="Evidence → Pain → Merchant → Product">
    <EmptyVisual code="LINEAGE REQUIRED" title="Sankey withheld until entity-level lineage is available">Stage totals are not treated as conversion flows. This prevents a visually impressive but analytically false Sankey.</EmptyVisual>
   </Panel>
  </div>

  <Panel eyebrow="AUDITABLE MARKET GRID" title="Every visual resolves back to production rows" aside={<span className={styles.legend}>Click headers to sort</span>}>
   {rows.length?<div className={styles.tableWrap}><table><thead>{table.getHeaderGroups().map(g=><tr key={g.id}>{g.headers.map(h=><th key={h.id} onClick={h.column.getToggleSortingHandler()}>{flexRender(h.column.columnDef.header,h.getContext())}{h.column.getIsSorted()==='asc'?' ↑':h.column.getIsSorted()==='desc'?' ↓':''}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.slice(0,60).map(r=><tr key={r.id}>{r.getVisibleCells().map(c=><td key={c.id}>{flexRender(c.column.columnDef.cell??c.column.columnDef.accessorKey,c.getContext())}</td>)}</tr>)}</tbody></table></div>:<EmptyVisual title="No trusted market rows">Run the semantic category evidence pipeline first.</EmptyVisual>}
  </Panel>

  {ai&&<motion.section className={styles.aiPanel} initial={{opacity:0,y:14}} animate={{opacity:1,y:0}}><div><span>AI INTELLIGENCE ANALYST</span><h2>Evidence-bounded interpretation</h2><p>{ai.market_outlook||ai.executive_summary||'Forecast generated from the current production snapshot.'}</p></div><aside><b>Confidence {fmt(ai.confidence_0_100)}%</b><small>{ai.methodology_note||'Directional indices only.'}</small>{(ai.affiliate_actions||[]).slice(0,5).map((x,i)=><div key={i}>{typeof x==='string'?x:JSON.stringify(x)}</div>)}</aside></motion.section>}

  <footer className={styles.footer}>Production snapshot {data?.generated_at?new Date(data.generated_at).toLocaleString('el-GR'):'—'} · Existing intelligence preserved · Missing ≠ zero · Modeled ≠ observed</footer>
 </main>
}
