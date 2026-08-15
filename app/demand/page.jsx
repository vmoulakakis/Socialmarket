'use client';

import {useCallback,useEffect,useMemo,useState} from 'react';
import {motion} from 'motion/react';
import {flexRender,getCoreRowModel,getSortedRowModel,useReactTable} from '@tanstack/react-table';
import {supabase} from '@/lib/supabase';
import EChart from '@/components/analytics/EChart';
import styles from './demand.module.css';

const valid=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const fmt=(v,d=0)=>valid(v)?Number(v).toLocaleString('el-GR',{maximumFractionDigits:d}):'—';
const pct=v=>valid(v)?`${fmt(Number(v)*100,0)}%`:'—';
const label=x=>x?.subcategory_name||x?.category_name||x?.taxonomy_name||'Unclassified';
const list=v=>Array.isArray(v)?v:[];
const palette={text:'#edf3fb',muted:'#7f8ba0',line:'rgba(148,163,184,.16)',violet:'#8b5cf6',cyan:'#22d3ee',emerald:'#34d399',amber:'#fbbf24',red:'#fb7185',blue:'#60a5fa'};

function Stat({label,value,meta,tone='violet'}){return <div className={styles.stat}><span>{label}</span><strong data-tone={tone}>{value}</strong><small>{meta}</small></div>}
function Empty({title,children,code}){return <div className={styles.emptyVisual}>{code&&<span>{code}</span>}<b>{title}</b><p>{children}</p></div>}
function Scene({index,eyebrow,title,aside,children,className=''}){return <section className={`${styles.scene} ${className}`}><header className={styles.sceneHead}><div className={styles.sceneIndex}>{String(index).padStart(2,'0')}</div><div><span>{eyebrow}</span><h2>{title}</h2></div>{aside&&<aside>{aside}</aside>}</header>{children}</section>}
function TruthChip({tone='derived',children}){return <span className={styles.truthChip} data-tone={tone}>{children}</span>}
function ErrorBox({children}){return children?<div className={styles.error}>{children}</div>:null}

export default function DemandIntelligence(){
 const [data,setData]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [selectedId,setSelectedId]=useState(''),[sorting,setSorting]=useState([]),[deep,setDeep]=useState(null),[deepBusy,setDeepBusy]=useState(false),[deepError,setDeepError]=useState('');

 const authFetch=useCallback(async(url,options={})=>{
  const {data:{session}}=await supabase.auth.getSession();
  if(!session?.access_token)throw new Error('Admin session expired. Sign in again.');
  const r=await fetch(url,{...options,headers:{...(options.headers||{}),authorization:`Bearer ${session.access_token}`}});
  const text=await r.text();let j;try{j=text?JSON.parse(text):null}catch{j={error:text||`HTTP ${r.status}`}}
  if(!r.ok||j?.error)throw new Error(j?.detail||j?.error||`HTTP ${r.status}`);
  return j;
 },[]);

 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{
   const j=await authFetch('/api/admin-dashboard',{cache:'no-store'});setData(j);
   const rows=list(j?.category_market),first=[...rows].filter(x=>valid(x.demand_score)).sort((a,b)=>Number(b.opportunity_score??b.demand_score)-Number(a.opportunity_score??a.demand_score))[0];
   if(first)setSelectedId(v=>v||first.taxonomy_id);
  }catch(e){setError(String(e?.message||e))}finally{setLoading(false)}
 },[authFetch]);
 useEffect(()=>{void load()},[load]);

 const allRows=useMemo(()=>list(data?.category_market),[data]);
 const selected=useMemo(()=>allRows.find(x=>x.taxonomy_id===selectedId)||allRows[0]||null,[allRows,selectedId]);
 const comparable=useMemo(()=>allRows.filter(x=>valid(x.demand_score)&&valid(x.competition_score)),[allRows]);
 const ranked=useMemo(()=>[...allRows].filter(x=>valid(x.demand_score)||valid(x.competition_score)||valid(x.opportunity_score)).sort((a,b)=>Number(b.opportunity_score??b.demand_score??-1)-Number(a.opportunity_score??a.demand_score??-1)),[allRows]);

 const loadDeep=useCallback(async(action='context')=>{
  if(!selectedId)return;setDeepBusy(true);setDeepError('');
  try{
   const j=await authFetch('/api/demand-intelligence',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action,taxonomy_id:selectedId,limit:90})});
   setDeep(j);if(j.ai_error)setDeepError(`AI synthesis unavailable: ${j.ai_error}`);
  }catch(e){setDeepError(String(e?.message||e));if(action==='context')setDeep(null)}finally{setDeepBusy(false)}
 },[authFetch,selectedId]);
 useEffect(()=>{if(selectedId)void loadDeep('context')},[selectedId,loadDeep]);

 const context=deep?.context||{},det=deep?.deterministic||{},analysis=deep?.analysis||null;
 const evidence=list(context.retrieved_evidence),supply=list(context.supply_context),history=list(context.history),sourceMix=list(context.source_mix);
 const fuzzy=det?.fuzzy_state||{},forecastGate=det?.forecast_gate||{},evidenceQuality=det?.evidence_quality||{},supplyDiag=det?.supply||{};
 const headline=analysis?.executive_thesis?.headline||(selected?`${label(selected)}: demand signal under deep evidence review`:'Demand Intelligence V3');
 const summary=analysis?.executive_thesis?.summary||(selected?`Canonical demand ${fmt(selected.demand_score)}, competition ${fmt(selected.competition_score)}, pain ${fmt(selected.pain_gap_score)} and opportunity ${fmt(selected.opportunity_score)} remain read-only. V3 adds evidence retrieval, uncertainty, supply context and forecast readiness around them.`:'Select a semantic market node to begin.');

 const scatter=useMemo(()=>({backgroundColor:'transparent',animationDuration:650,grid:{left:55,right:30,top:34,bottom:54},xAxis:{name:'Competition →',min:0,max:100,nameLocation:'middle',nameGap:35,axisLabel:{color:palette.muted},axisLine:{lineStyle:{color:palette.line}},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{name:'Demand →',min:0,max:100,nameLocation:'middle',nameGap:40,axisLabel:{color:palette.muted},axisLine:{lineStyle:{color:palette.line}},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},tooltip:{backgroundColor:'#09111d',borderColor:palette.line,textStyle:{color:palette.text},formatter:p=>{const v=p.data;return `<b>${v[5]}</b><br/>Demand ${fmt(v[1])}<br/>Competition ${fmt(v[0])}<br/>Opportunity ${fmt(v[3])}<br/>Evidence ${fmt(v[2])}<br/>Confidence ${valid(v[4])?fmt(v[4]*100)+'%':'—'}`}},visualMap:{show:false,min:0,max:100,dimension:3,inRange:{color:['#475569',palette.cyan,palette.violet,palette.emerald]}},series:[{type:'scatter',data:comparable.map(x=>[Number(x.competition_score),Number(x.demand_score),Number(x.evidence_entities||0),Number(x.opportunity_score||0),valid(x.confidence)?Number(x.confidence):null,label(x),x.taxonomy_id]),symbolSize:v=>Math.max(11,Math.min(42,11+Math.sqrt(Math.max(0,v[2]))*3)),itemStyle:{opacity:.8,borderColor:'rgba(255,255,255,.3)',borderWidth:1},emphasis:{scale:1.18,itemStyle:{opacity:1}},markArea:{silent:true,label:{color:'rgba(226,232,240,.45)',fontSize:10},itemStyle:{opacity:.045},data:[[{name:'WHITESPACE',xAxis:0,yAxis:50,itemStyle:{color:palette.emerald}},{xAxis:50,yAxis:100}],[{name:'CROWDED DEMAND',xAxis:50,yAxis:50,itemStyle:{color:palette.amber}},{xAxis:100,yAxis:100}],[{name:'EMERGING',xAxis:0,yAxis:0,itemStyle:{color:palette.cyan}},{xAxis:50,yAxis:50}],[{name:'VALIDATE',xAxis:50,yAxis:0,itemStyle:{color:palette.red}},{xAxis:100,yAxis:50}]]}}]}),[comparable]);
 const scatterEvents=useMemo(()=>({click:p=>{const id=p?.data?.[6];if(id)setSelectedId(String(id))}}),[]);

 const signalChart=useMemo(()=>{if(!selected)return null;const pairs=[['Demand',selected.demand_score,palette.cyan],['Competition',selected.competition_score,palette.amber],['Pain gap',selected.pain_gap_score,palette.red],['Opportunity',selected.opportunity_score,palette.emerald],['Confidence',valid(selected.confidence)?Number(selected.confidence)*100:null,palette.violet]].filter(x=>valid(x[1]));return {backgroundColor:'transparent',grid:{left:88,right:24,top:8,bottom:22},xAxis:{type:'value',min:0,max:100,axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{type:'category',inverse:true,data:pairs.map(x=>x[0]),axisLabel:{color:'#b9c5d5'},axisLine:{show:false},axisTick:{show:false}},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:'#09111d',borderColor:palette.line,textStyle:{color:palette.text}},series:[{type:'bar',barMaxWidth:18,data:pairs.map(x=>({value:Number(x[1]),itemStyle:{color:x[2],borderRadius:[0,8,8,0]}}))}]};},[selected]);

 const fuzzyChart=useMemo(()=>{const pairs=Object.entries(fuzzy.membership||{}).sort((a,b)=>b[1]-a[1]);if(!pairs.length)return null;return {backgroundColor:'transparent',grid:{left:135,right:24,top:8,bottom:22},xAxis:{type:'value',min:0,max:1,axisLabel:{color:palette.muted,formatter:v=>`${Math.round(v*100)}%`},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{type:'category',inverse:true,data:pairs.map(x=>x[0].replaceAll('_',' ')),axisLabel:{color:'#b9c5d5',fontSize:10},axisLine:{show:false},axisTick:{show:false}},series:[{type:'bar',barMaxWidth:15,data:pairs.map(([k,v])=>({value:v,itemStyle:{color:k==='uncertain'?palette.amber:k===fuzzy.state?palette.violet:'#334155',borderRadius:[0,7,7,0]}}))}]};},[fuzzy]);

 const sourceChart=useMemo(()=>{if(!sourceMix.length)return null;return {backgroundColor:'transparent',grid:{left:110,right:28,top:8,bottom:28},xAxis:{type:'value',axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{type:'category',inverse:true,data:sourceMix.slice(0,12).map(x=>x.source_domain||'unknown'),axisLabel:{color:'#aeb9ca',fontSize:9,width:98,overflow:'truncate'},axisLine:{show:false},axisTick:{show:false}},tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:'#09111d',borderColor:palette.line,textStyle:{color:palette.text}},series:[{type:'bar',barMaxWidth:14,data:sourceMix.slice(0,12).map(x=>({value:Number(x.observations||0),itemStyle:{color:Number(x.avg_authority||0)>=.9?palette.emerald:palette.cyan,borderRadius:[0,6,6,0]}}))}]};},[sourceMix]);

 const historyChart=useMemo(()=>{const rows=[...history].sort((a,b)=>new Date(a.observed_at)-new Date(b.observed_at));if(rows.length<2)return null;const series=[['Demand','demand_score',palette.cyan],['Competition','competition_score',palette.amber],['Pain','pain_gap_score',palette.red],['Opportunity','opportunity_score',palette.emerald]].map(([name,key,color])=>({name,type:'line',showSymbol:rows.length<18,smooth:false,connectNulls:false,data:rows.map(x=>valid(x[key])?Number(x[key]):null),lineStyle:{width:2,color},itemStyle:{color}}));return {backgroundColor:'transparent',legend:{top:0,textStyle:{color:palette.muted,fontSize:10}},grid:{left:44,right:20,top:38,bottom:44},xAxis:{type:'category',data:rows.map(x=>new Date(x.observed_at).toLocaleString('el-GR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})),axisLabel:{color:palette.muted,fontSize:9,rotate:25},axisLine:{lineStyle:{color:palette.line}}},yAxis:{type:'value',min:0,max:100,axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},tooltip:{trigger:'axis',backgroundColor:'#09111d',borderColor:palette.line,textStyle:{color:palette.text}},series};},[history]);

 const supplyChart=useMemo(()=>{const rows=supply.filter(x=>valid(x.commercial_score)&&valid(x.trust_score));if(!rows.length)return null;return {backgroundColor:'transparent',grid:{left:48,right:24,top:24,bottom:44},xAxis:{name:'Commercial quality →',min:0,max:100,nameLocation:'middle',nameGap:30,axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},yAxis:{name:'Trust →',min:0,max:100,nameLocation:'middle',nameGap:36,axisLabel:{color:palette.muted},splitLine:{lineStyle:{color:'rgba(148,163,184,.07)'}}},tooltip:{backgroundColor:'#09111d',borderColor:palette.line,textStyle:{color:palette.text},formatter:p=>`<b>${p.data[3]}</b><br/>Commercial ${fmt(p.data[0])}<br/>Trust ${fmt(p.data[1])}<br/>Evidence ${fmt(p.data[2])}`},series:[{type:'scatter',data:rows.map(x=>[Number(x.commercial_score),Number(x.trust_score),Number(x.evidence_count||0),x.canonical_name]),symbolSize:v=>Math.max(10,Math.min(30,10+Math.sqrt(Math.max(0,v[2]))*2)),itemStyle:{color:palette.blue,opacity:.78,borderColor:'rgba(255,255,255,.25)',borderWidth:1}}]};},[supply]);

 const columns=useMemo(()=>[
  {accessorFn:r=>r.category_name||r.taxonomy_name||'—',id:'category',header:'Category',cell:i=>String(i.getValue()??'—')},
  {accessorFn:r=>r.subcategory_name||'Category level',id:'subcategory',header:'Subcategory',cell:i=>String(i.getValue()??'—')},
  {accessorKey:'demand_score',header:'Demand',cell:i=>fmt(i.getValue())},
  {accessorKey:'competition_score',header:'Competition',cell:i=>fmt(i.getValue())},
  {accessorKey:'pain_gap_score',header:'Pain',cell:i=>fmt(i.getValue())},
  {accessorKey:'opportunity_score',header:'Opportunity',cell:i=><b>{fmt(i.getValue())}</b>},
  {accessorKey:'confidence',header:'Confidence',cell:i=>pct(i.getValue())},
  {accessorKey:'evidence_entities',header:'Evidence',cell:i=>fmt(i.getValue())}
 ],[]);
 const table=useReactTable({data:allRows,columns,state:{sorting},onSortingChange:setSorting,getCoreRowModel:getCoreRowModel(),getSortedRowModel:getSortedRowModel()});

 if(loading)return <main className={styles.page}><div className={styles.loading}>Loading production demand intelligence…</div></main>;
 return <main className={styles.page}>
  <motion.header className={styles.hero} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}>
   <div className={styles.heroCopy}>
    <div className={styles.engineRow}><span className={styles.kicker}>DEMAND INTELLIGENCE V3 · GREECE</span><TruthChip tone="observed">PRODUCTION TRUTH</TruthChip><TruthChip tone="derived">AUTONOMOUS RAG + FUZZY</TruthChip><TruthChip tone={forecastGate.status==='SHADOW_BACKTEST_ELIGIBLE'?'modeled':'withheld'}>{forecastGate.status||'FORECAST GATED'}</TruthChip></div>
    <h1>{headline}</h1><p>{summary}</p>
    <div className={styles.truthRow}><TruthChip tone="observed">OBSERVED evidence</TruthChip><TruthChip tone="derived">DERIVED canonical indices</TruthChip><TruthChip tone="modeled">MODELED only after backtest</TruthChip><TruthChip tone="withheld">MISSING stays missing</TruthChip></div>
   </div>
   <div className={styles.heroActions}>
    <select value={selectedId} onChange={e=>setSelectedId(e.target.value)} aria-label="Select market node">{ranked.map(x=><option key={x.taxonomy_id} value={x.taxonomy_id}>{x.category_name}{x.subcategory_name?` / ${x.subcategory_name}`:''}</option>)}</select>
    <button onClick={load}>Refresh truth</button>
    <button className={styles.primary} onClick={()=>loadDeep('analyze')} disabled={deepBusy||!selected}>{deepBusy?'Deep analysis running…':'✦ Deep AI Research'}</button>
   </div>
  </motion.header>
  <ErrorBox>{error}</ErrorBox><ErrorBox>{deepError}</ErrorBox>

  <section className={styles.stats}>
   <Stat label="Canonical demand" value={fmt(selected?.demand_score)} meta="evidence-density proxy · not search volume" tone="cyan"/>
   <Stat label="Competition" value={fmt(selected?.competition_score)} meta={valid(selected?.competition_score)?'commercial-domain proxy':'missing remains missing'} tone="amber"/>
   <Stat label="Pain gap" value={fmt(selected?.pain_gap_score)} meta={`${fmt(selected?.validated_pain_clusters)} validated clusters`} tone="red"/>
   <Stat label="Opportunity" value={fmt(selected?.opportunity_score)} meta="existing production formula" tone="emerald"/>
   <Stat label="Evidence RAG" value={fmt(evidenceQuality.observations)} meta={`${fmt(evidenceQuality.independent_domains)} independent domains`} tone="violet"/>
   <Stat label="Supply context" value={fmt(supplyDiag.merchant_count)} meta={valid(supplyDiag.analytical_supply_strength)?`derived strength ${fmt(supplyDiag.analytical_supply_strength)}`:'exact-taxonomy merchants'} tone="blue"/>
  </section>

  <Scene index={1} eyebrow="EXECUTIVE THESIS" title="What the Greek market is actually telling us" aside={<div className={styles.metaStack}><span>{label(selected)}</span><small>{selected?.observed_at?new Date(selected.observed_at).toLocaleString('el-GR'):'—'}</small></div>} className={styles.thesisScene}>
   <div className={styles.thesisGrid}><div><h3>{analysis?.executive_thesis?.headline||headline}</h3><p>{analysis?.executive_thesis?.summary||'Run Deep AI Research to turn the deterministic evidence bundle into a skeptical executive thesis. The underlying scores will not change.'}</p></div><div className={styles.thesisFacts}><div><span>Fuzzy market state</span><b>{String(fuzzy.state||'awaiting context').replaceAll('_',' ')}</b><small>analytical description, not a new score</small></div><div><span>AI thesis confidence</span><b>{analysis?.executive_thesis?.confidence_0_100!=null?`${fmt(analysis.executive_thesis.confidence_0_100)}%`:'—'}</b><small>{analysis?.executive_thesis?.confidence_basis||`Canonical confidence ${pct(selected?.confidence)}`}</small></div></div></div>
  </Scene>

  <Scene index={2} eyebrow="MARKET LANDSCAPE" title="Demand × Competition · select any bubble" aside="Bubble = evidence footprint · color = canonical opportunity">
   {comparable.length?<EChart option={scatter} onEvents={scatterEvents} height={510} ariaLabel="Demand and competition landscape"/>:<Empty code="NO COMPARABLE ROWS" title="Competition evidence is incomplete">Rows need both demand and competition to enter this landscape.</Empty>}
  </Scene>

  <div className={styles.sceneGrid2}>
   <Scene index={3} eyebrow="SIGNAL DECOMPOSITION" title="Canonical signal, without AI rescore">{signalChart?<EChart option={signalChart} height={350} ariaLabel="Canonical market signal decomposition"/>:<Empty title="No canonical metrics">No comparable market metrics are available.</Empty>}</Scene>
   <Scene index={4} eyebrow="FUZZY UNCERTAINTY" title="State memberships, not a replacement score">{fuzzyChart?<EChart option={fuzzyChart} height={350} ariaLabel="Fuzzy market state memberships"/>:<Empty code="CONTEXT REQUIRED" title="Fuzzy engine awaits deep context">Select a node and let the deterministic context load.</Empty>}</Scene>
  </div>

  <Scene index={5} eyebrow="HYBRID RAG" title="Evidence stack behind the thesis" aside={<div className={styles.metaStack}><span>{fmt(evidenceQuality.observations)} retrieved</span><small>direct + FTS + fuzzy + authority + recency</small></div>}>
   {evidence.length?<div className={styles.evidenceGrid}>{evidence.slice(0,12).map((x,i)=><article className={styles.evidenceCard} key={x.id||`${x.source_url}-${i}`}><div><TruthChip tone="observed">{String(x.source_kind||'evidence').toUpperCase()}</TruthChip><span className={styles.rank}>RAG {valid(x?.retrieval?.score)?fmt(Number(x.retrieval.score)*100,0):'—'}</span></div><h3>{x.title||x.source_domain||'Evidence observation'}</h3><p>{String(x.body||'').slice(0,360)}</p><footer><span>{x.source_domain||'unknown domain'}</span><span>conf. {pct(x.confidence)}</span>{x.source_url&&<a href={x.source_url} target="_blank" rel="noreferrer">source ↗</a>}</footer></article>)}</div>:<Empty code={deepBusy?'RETRIEVING':'NO MATCHED EVIDENCE'} title={deepBusy?'Hybrid retrieval is running':'No retrievable evidence for this node'}>The engine will not synthesize a story without a retrievable evidence bundle.</Empty>}
  </Scene>

  <div className={styles.sceneGrid2}>
   <Scene index={6} eyebrow="GREEK SOURCE CONTEXT" title="Authority and source diversity">
    {sourceChart?<EChart option={sourceChart} height={360} ariaLabel="Greek market evidence source mix"/>:<Empty title="No source mix yet">Authority is calculated only from evidence actually retrieved for this node.</Empty>}
    {list(analysis?.greek_context).length>0&&<div className={styles.insightList}>{analysis.greek_context.slice(0,6).map((x,i)=><div key={i}><TruthChip tone={x.classification==='OBSERVED'?'observed':'derived'}>{x.classification||'DERIVED'}</TruthChip><b>{x.finding}</b><p>{x.evidence}</p><small>{x.source} · {x.limits}</small></div>)}</div>}
   </Scene>
   <Scene index={7} eyebrow="DEMAND ↔ SUPPLY" title="Does affiliate supply answer the demand?">
    {supplyChart?<EChart option={supplyChart} height={360} ariaLabel="Merchant supply commercial quality versus trust"/>:<Empty title="No exact-taxonomy supply rows">Supply is not inferred from unrelated merchants.</Empty>}
    <div className={styles.supplySummary}><div><span>Unique merchants</span><b>{fmt(supplyDiag.merchant_count)}</b></div><div><span>Avg trust</span><b>{fmt(supplyDiag.avg_trust,1)}</b></div><div><span>Avg commercial</span><b>{fmt(supplyDiag.avg_commercial,1)}</b></div><div><span>Risk rate</span><b>{valid(supplyDiag.risk_rate)?pct(supplyDiag.risk_rate):'—'}</b></div></div>
    {analysis?.supply_response&&<div className={styles.callout}><b>{analysis.supply_response.assessment}</b><p>{analysis.supply_response.relationship_to_demand}</p><small>{analysis.supply_response.causality_warning}</small></div>}
   </Scene>
  </div>

  <Scene index={8} eyebrow="SKEPTIC PASS" title="Contradictions, weak links and what would change the thesis">
   <div className={styles.sceneGrid2}>
    <div>{list(analysis?.contradictions).length?<div className={styles.insightList}>{analysis.contradictions.slice(0,7).map((x,i)=><div key={i}><TruthChip tone={x.status==='explicit_conflict'?'withheld':'derived'}>{x.status||'unresolved'}</TruthChip><b>{x.claim}</b><p><strong>Support:</strong> {x.supporting||'—'}</p><p><strong>Counter:</strong> {x.contradicting||'—'}</p></div>)}</div>:<Empty code="NO AI SKEPTIC PASS YET" title="Absence is not contradiction">Deep AI Research explicitly searches the retrieved bundle for disconfirming evidence.</Empty>}</div>
    <div>{list(analysis?.falsification_tests).length?<div className={styles.insightList}>{analysis.falsification_tests.slice(0,7).map((x,i)=><div key={i}><TruthChip tone="withheld">FALSIFICATION</TruthChip><b>{x.thesis}</b><p>{x.test}</p><small>Would falsify: {x.would_falsify}</small></div>)}</div>:<Empty title="Falsification tests will appear here">A strong market thesis must say what evidence would prove it wrong.</Empty>}</div>
   </div>
  </Scene>

  <Scene index={9} eyebrow="TEMPORAL EVIDENCE" title="Observed history — descriptive, never decorative">
   {historyChart?<EChart option={historyChart} height={410} ariaLabel="Observed category market history"/>:<Empty code="INSUFFICIENT HISTORY" title="No fake trend line">At least two persisted observations are required to draw a historical path.</Empty>}
   <div className={styles.historyMeta}><span>{fmt(det?.history?.points)} points</span><span>{fmt(det?.history?.unique_days)} unique days</span><span>{fmt(det?.history?.span_days,1)} day span</span><span>Demand Δ {valid(det?.history?.descriptive_delta?.demand)?`${det.history.descriptive_delta.demand>=0?'+':''}${fmt(det.history.descriptive_delta.demand,1)}`:'—'}</span></div>
  </Scene>

  <Scene index={10} eyebrow="FORECAST LAB" title="Neural networks earn the right to forecast" aside={<TruthChip tone={forecastGate.status==='SHADOW_BACKTEST_ELIGIBLE'?'modeled':'withheld'}>{forecastGate.status||'WITHHELD'}</TruthChip>}>
   <div className={styles.forecastLab}><div><span>History gate</span><b>{forecastGate.eligible?'Eligible for shadow backtest':'Forecast withheld'}</b><p>{forecastGate.eligible?'Neural/foundation challengers may now be evaluated against naive baselines. They are still not production forecasts.':`Current temporal evidence does not satisfy the production gate: ${list(forecastGate.reasons).join(', ')||'insufficient history'}.`}</p></div><div><span>Challenger stack</span><b>NHITS · NBEATSx · PatchTST · TFT</b><p>TimesFM · Chronos-2 · Darts validation · Hierarchical reconciliation. Complexity is promoted only after out-of-sample superiority.</p></div><div><span>Production rule</span><b>Backtest &gt; model prestige</b><p>{forecastGate.rule||'No neural model is promoted merely because it is more sophisticated.'}</p></div></div>
   {analysis?.forecast_lab&&<div className={styles.callout}><b>{analysis.forecast_lab.status}</b><p>{analysis.forecast_lab.why}</p><small>Next gate: {analysis.forecast_lab.next_gate}</small></div>}
  </Scene>

  <Scene index={11} eyebrow="DECISION LAYER" title="Affiliate actions grounded in the evidence">
   <div className={styles.sceneGrid3}>
    <div><h3 className={styles.columnTitle}>Recommended actions</h3>{list(analysis?.recommended_actions).length?<div className={styles.insightList}>{analysis.recommended_actions.slice(0,7).map((x,i)=><div key={i}><TruthChip tone="derived">{x.priority||'PRIORITY'}</TruthChip><b>{x.action}</b><p>{x.why}</p><small>Watch: {x.metric_to_watch} · Need: {x.evidence_needed}</small></div>)}</div>:<Empty title="Run Deep AI Research">The analyst will recommend actions only after evidence retrieval and skeptical synthesis.</Empty>}</div>
    <div><h3 className={styles.columnTitle}>Affiliate implications</h3>{list(analysis?.affiliate_implications).length?<div className={styles.insightList}>{analysis.affiliate_implications.slice(0,7).map((x,i)=><div key={i}><TruthChip tone="derived">{x.priority||'IMPLICATION'}</TruthChip><b>{x.implication}</b><p>{x.evidence}</p><small>Do not assume: {x.what_not_to_assume}</small></div>)}</div>:<Empty title="No implication invented">Network economics alone are not treated as first-party performance.</Empty>}</div>
    <div><h3 className={styles.columnTitle}>Next evidence</h3>{list(analysis?.next_evidence_to_collect).length?<div className={styles.insightList}>{analysis.next_evidence_to_collect.slice(0,7).map((x,i)=><div key={i}><TruthChip tone="observed">{x.priority||'COLLECT'}</TruthChip><b>{x.evidence}</b><p>{x.why}</p><small>{x.source_family}</small></div>)}</div>:<Empty title="Evidence acquisition plan pending">The autonomous agent will identify the evidence with the highest decision value.</Empty>}</div>
   </div>
  </Scene>

  <Scene index={12} eyebrow="AUDITABLE MARKET GRID" title="Every visual resolves back to canonical production rows" aside="Click headers to sort">
   {allRows.length?<div className={styles.tableWrap}><table><thead>{table.getHeaderGroups().map(g=><tr key={g.id}>{g.headers.map(h=><th key={h.id} onClick={h.column.getToggleSortingHandler()}>{flexRender(h.column.columnDef.header,h.getContext())}{h.column.getIsSorted()==='asc'?' ↑':h.column.getIsSorted()==='desc'?' ↓':''}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(r=><tr key={r.id} data-selected={r.original.taxonomy_id===selectedId} onClick={()=>setSelectedId(r.original.taxonomy_id)}>{r.getVisibleCells().map(c=><td key={c.id}>{flexRender(c.column.columnDef.cell,c.getContext())}</td>)}</tr>)}</tbody></table></div>:<Empty title="No semantic market rows">No category-market truth is available.</Empty>}
  </Scene>

  <footer className={styles.footer}>SocialMarket Demand Intelligence V3 · canonical truth immutable · RAG retrieves · fuzzy logic interprets uncertainty · neural forecasting stays gated · user override available</footer>
 </main>
}
