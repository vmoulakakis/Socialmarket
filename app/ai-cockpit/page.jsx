'use client';

import {useCallback,useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import EChart from '@/components/analytics/EChart';
import styles from './cockpit.module.css';

const TABS=[
 ['overview','◫','Mission control'],
 ['catalog','▤','Catalog & merchants'],
 ['intelligence','◇','AI intelligence'],
 ['operations','⚙','Operations & audit']
];
const nf=n=>Number(n??0).toLocaleString('el-GR',{maximumFractionDigits:1});
const dt=s=>s?new Date(s).toLocaleString('el-GR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
const short=s=>String(s||'').replaceAll('_',' ').replaceAll('linkwise cd104','Linkwise CD104');
const scoreColor=(v)=>v==='completed'||v==='active'||v==='verified'?'positive':v==='failed'||v==='error'||v==='blocked'?'negative':'caution';

function Tile({icon,label,value,sub,tone='neutral',bar}){
 return <article className={styles.tile}>
  <div className={styles.tileTop}><span>{label}</span><span className={styles.tileIcon}>{icon}</span></div>
  <strong>{value}</strong><small className={styles[tone]}>{sub}</small>
  {typeof bar==='number'&&<div className={styles.meter}><i style={{width:`${Math.min(100,Math.max(0,bar))}%`}}/></div>}
 </article>;
}
function Panel({label,title,extra,children,className=''}){return <section className={styles.panel+' '+className}><div className={styles.panelHead}><div><small className={styles.eyebrow}>{label}</small><h2>{title}</h2></div>{extra}</div>{children}</section>}
function Pill({children,tone='caution'}){return <span className={styles.pill+' '+styles[tone]}>{children}</span>}
function Bar({label,count,max,color='blue'}){const val=Number(count||0);return <div className={styles.barLine}><div className={styles.barLabel}><span title={label}>{label}</span><b>{nf(val)}</b></div><div className={styles.track}><i className={styles[color]} style={{width:`${max?Math.max(1,100*val/max):0}%`}}/></div></div>}
function Empty({text='Δεν υπάρχουν ακόμη καταχωρισμένα δεδομένα.'}){return <p className={styles.empty}>{text}</p>}

export default function SocialMarketCockpit(){
 const [data,setData]=useState(null),[tab,setTab]=useState('overview');
 const [error,setError]=useState(''),[message,setMessage]=useState('');
 const [busy,setBusy]=useState(''),[loading,setLoading]=useState(true);
 const [search,setSearch]=useState(''),[searchData,setSearchData]=useState(null);
 const [searching,setSearching]=useState(false),[lastRefresh,setLastRefresh]=useState(null);
 const load=useCallback(async(silent=false)=>{
  if(!silent)setLoading(true);
  try{
   const {data:auth,error:authErr}=await supabase.auth.getSession();
   const token=auth?.session?.access_token;
   if(authErr||!token)throw new Error('Απαιτείται σύνδεση διαχειριστή.');
   const res=await fetch('/api/ai-cockpit',{headers:{authorization:`Bearer ${token}`},cache:'no-store'});
   const payload=await res.json();
   if(!res.ok||!payload?.health)throw new Error('Δεν ήταν δυνατή η ανάκτηση του VMDB control plane.');
   setData(payload);setLastRefresh(new Date());setError('');
  }catch(e){setError(e?.message||'Αποτυχία επικοινωνίας με το VMDB');}
  finally{setLoading(false)}
 },[]);
 useEffect(()=>{load();const timer=setInterval(()=>load(true),60000);return()=>clearInterval(timer)},[load]);
 const run=async(action,target=null)=>{
  const labels={sync_search_docs:'Ενημέρωση του search index χωρίς embeddings',queue_research:'Ενημέρωση της ουράς research',pause_objective:'Παύση agent objective',resume_objective:'Ενεργοποίηση agent objective'};
  if(!window.confirm(`${labels[action]||action}\n\nΗ ενέργεια καταγράφεται στο audit log. Συνέχεια;`))return;
  setBusy(action+':'+(target||''));setMessage('');setError('');
  try{
   const {data:auth}=await supabase.auth.getSession();const token=auth?.session?.access_token;
   if(!token)throw new Error('Η συνεδρία έληξε.');
   const res=await fetch('/api/ai-cockpit',{method:'POST',
    headers:{authorization:`Bearer ${token}`,'content-type':'application/json'},
    body:JSON.stringify({action,target})});
   const outcome=await res.json();
   if(!res.ok||!outcome?.ok)throw new Error('Η ενέργεια δεν εγκρίθηκε από το backend.');
   setMessage('Επιτυχής ενέργεια: '+labels[action]);await load(true);
  }catch(e){setError(e?.message||'Αποτυχία ενέργειας')}
  finally{setBusy('')}
 };
 const doSearch=async(e)=>{
  e.preventDefault();const q=search.trim();if(q.length<2)return;
  setSearching(true);setSearchData(null);
  try{
   const {data:auth}=await supabase.auth.getSession();if(!auth?.session?.access_token)throw new Error('Admin session required');
   const r=await fetch('/api/ai-cockpit?q='+encodeURIComponent(q),{cache:'no-store',
    headers:{authorization:'Bearer '+auth.session.access_token}});
   if(!r.ok)throw new Error('Η αναζήτηση απέτυχε.');
   setSearchData(await r.json());
  }catch(e){setError(e?.message||'Search unavailable');}finally{setSearching(false)}
 };
 const h=data?.health||{}, alerts=(data?.alerts||[]).filter(x=>x.active), goals=data?.objectives||[];
 const runs=data?.feeds||[], agentRuns=data?.agent_runs||[];
 const allRoles=data?.agent_roles||[], byRoles={};
 allRoles.forEach(x=>{const id=x.agent_role;byRoles[id]=(byRoles[id]||0)+Number(x.n||0)});
 const roleChart=useMemo(()=>({
   backgroundColor:'transparent',grid:{left:16,right:18,top:16,bottom:50,containLabel:true},
   tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:'#182439',borderColor:'#304157',textStyle:{color:'#fff'}},
   xAxis:{type:'category',data:Object.keys(byRoles).map(k=>k.replaceAll('_',' ')),axisLabel:{color:'#9eafc5',interval:0,rotate:29,fontSize:10},axisLine:{lineStyle:{color:'#344257'}}},
   yAxis:{type:'value',axisLabel:{color:'#8294a9'},splitLine:{lineStyle:{color:'#27354a'}}},
   series:[{type:'bar',data:Object.values(byRoles),barMaxWidth:32,itemStyle:{color:'#67d8ab',borderRadius:[5,5,0,0]}}]
 }),[data]);
 const catalogChart=useMemo(()=>({
  backgroundColor:'transparent',grid:{top:6,left:6,right:22,bottom:5,containLabel:true},
  tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:'#182439',textStyle:{color:'#fff'}},
  xAxis:{type:'value',axisLabel:{color:'#9aacc4'},splitLine:{lineStyle:{color:'#27364a'}}},
  yAxis:{type:'category',inverse:true,data:(data?.categories||[]).map(x=>x.label),axisLabel:{color:'#a7b7cb',fontSize:10,width:110,overflow:'truncate'},axisLine:{show:false},axisTick:{show:false}},
  series:[{type:'bar',data:(data?.categories||[]).map(x=>Number(x.n)),barMaxWidth:17,itemStyle:{color:'#6e9df8',borderRadius:[0,4,4,0]}}]
 }),[data]);
 const percent=(a,b)=>Number(b)?Math.round(100*Number(a||0)/Number(b)):0;
 const sideAlerts=alerts.slice(0,5);
 return <main className={styles.frame}>
  <header className={styles.topbar}>
   <div><div className={styles.kicker}><span className={styles.liveDot}/> PRIVATE • VMDB / SOCIALMARKET INTELLIGENCE</div>
    <h1>AI Control Cockpit <span>01 / Command</span></h1>
    <p>Ενιαίο κέντρο διαχείρισης για δεδομένα, agents, εμπορική επιλεξιμότητα και Hybrid GraphRAG.</p></div>
   <div className={styles.topActions}>
    <div className={styles.liveText}><span className={styles.liveDot}/><b>READ-ONLY BY DEFAULT</b><small>Last sync: {lastRefresh?dt(lastRefresh):'—'} · 60s refresh</small></div>
    <button className={styles.refresh} onClick={()=>load()} disabled={loading||!!busy} title="Refresh dashboard" aria-label="Ανανέωση"><span>↻</span> Refresh</button>
   </div>
  </header>
  <div className={styles.tabRow}>
   {TABS.map(([key,ico,title])=><button type="button" key={key} className={tab===key?styles.tabActive:''} onClick={()=>setTab(key)}><span>{ico}</span>{title}</button>)}
   <span className={styles.privateTag}>◈ ADMIN ONLY</span>
  </div>
  {(error||message)&&<div role="status" className={error?styles.error:styles.success}>{error||message}<button onClick={()=>{setError('');setMessage('')}} aria-label="Close message">×</button></div>}
  {loading&&!data?<div className={styles.loading}><div className={styles.spinner}/>Σύνδεση με το VMDB και ανάκτηση πραγματικών KPIs…</div>:!data?<div className={styles.loading}>Δεν επιστράφηκαν δεδομένα. Έλεγξε τη συνεδρία και το backend. <button onClick={()=>load()}>Retry</button></div>:
  <div className={styles.body}>
   {tab==='overview'&&<>
    <section className={styles.kpiRow}>
     <Tile icon="▣" label="RAW PRODUCT CATALOG" value={nf(h.raw_products)} sub="Ιστορικές καταχωρίσεις · όχι απαραίτητα πρόσφατες" tone="neutral" bar={percent(h.fresh_products_7d,h.raw_products)}/>
     <Tile icon="◇" label="MERCHANT PROGRAMS" value={nf(h.merchant_program_rows)} sub={nf(h.missing_program_ids)+' χωρίς επίσημο ID'} tone="caution" bar={percent(Number(h.merchant_program_rows)-Number(h.missing_program_ids),h.merchant_program_rows)}/>
     <Tile icon="▧" label="SEARCHABLE DOCS" value={nf(h.searchable_docs)} sub={nf(h.vector_docs)+' vectors ready'} tone={Number(h.vector_docs)?'positive':'caution'} bar={percent(h.vector_docs,h.searchable_docs)}/>
     <Tile icon="◉" label="AFFILIATE READY" value={nf(h.promotion_ready_offers)} sub="Υπολογισμένη προμήθεια ≥10€ και επαληθευμένα" tone={Number(h.promotion_ready_offers)?'positive':'negative'}/>
     <Tile icon="⌘" label="AGENT TASKS" value={nf(h.agent_tasks)} sub={nf(h.agent_queued)+' στην ουρά'} tone="neutral" bar={percent(Number(h.agent_tasks)-Number(h.agent_queued),h.agent_tasks)}/>
    </section>
    <div className={styles.overviewGrid}>
     <Panel label="INTELLIGENCE PIPELINE" title="Η κατάσταση ολόκληρου του backend" className={styles.wide}>
      <div className={styles.pipeline}>
       {[['1','Source Feed',h.raw_products,'Source catalog'],['2','Merchant ID',Number(h.merchant_program_rows)-Number(h.missing_program_ids),'Identifiers'],['3','Verified Terms',h.verified_commission_terms,'Commercial rules'],['4','Semantic Index',h.vector_docs,'E5 vectors'],['5','Approved Offers',h.promotion_ready_offers,'Market ready']].map(([i,n,v,desc],j)=><div className={styles.pipeStep} key={n}>
         <div className={styles.pipeHead}><span>{i.padStart(2,'0')}</span><span className={Number(v)>0?styles.pipeGood:styles.pipeWait}>{Number(v)>0?'●':'○'}</span></div>
         <strong>{nf(v)}</strong><b>{n}</b><small>{desc}</small>
        </div>)}
      </div>
      <p className={styles.footNote}>Κάθε στάδιο μετριέται ανεξάρτητα. Τα 334 προγράμματα δεν ισοδυναμούν με 334 εγκεκριμένους εμπόρους.</p>
     </Panel>
     <Panel label="ACTION PRIORITIES" title="Τι εμποδίζει την παραγωγή">
      <div className={styles.alertStack}>{sideAlerts.map((a,i)=><div className={styles.alert} key={i}><span className={a.level==='critical'?styles.dangerMark:styles.warnMark}>!</span><div><strong>{a.title}</strong><small>{a.detail}</small></div><Pill tone={a.level==='critical'?'negative':'caution'}>{a.level}</Pill></div>)}
      {sideAlerts.length===0&&<Empty text="Δεν αναφέρθηκαν ενεργά alerts από το backend."/>}</div>
     </Panel>
     <Panel label="MODEL GOVERNANCE" title="Κόστος και AI budgets">
      <div className={styles.budgetStack}>{(data.budgets||[]).slice(0,6).map(b=><div key={b.metric} className={styles.budgetItem}><div><strong>{short(b.metric)}</strong><span>{nf(b.used_today)} / {nf(b.daily_limit)} today</span></div><div className={styles.track}><i className={styles.blue} style={{width:`${percent(b.used_today,b.daily_limit)}%`}}/></div></div>)}</div>
      <small className={styles.note}>Εμφανίζονται πραγματικές κρατήσεις και καταναλώσεις, όχι εκτιμήσεις κόστους.</small>
     </Panel>
     <Panel label="ORCHESTRATION" title="Εργασίες ανά ρόλο">
      <EChart option={roleChart} height={224} ariaLabel="Agent tasks by specialist role"/>
     </Panel>
    </div>
   </>}
   {tab==='catalog'&&<>
    <section className={styles.kpiRow}>
     <Tile label="TOTAL IMPORTS" icon="◫" value={nf(h.raw_products)} sub="Όλες οι ιστορικές εγγραφές"/>
     <Tile label="FRESH < 7 DAYS" icon="◷" value={nf(h.fresh_products_7d)} sub="Απαιτείται ασφαλές refresh" tone={Number(h.fresh_products_7d)?'positive':'caution'}/>
     <Tile label="SOURCE PROGRAMS" icon="▣" value={nf(h.merchant_program_rows)} sub="Merchant source records"/>
     <Tile label="UNKNOWN VALID-TO" icon="◴" value={nf(h.unknown_terms_valid_to)} sub="Δεν υποθέτουμε ενεργή σύμβαση" tone="caution"/>
     <Tile label="QUALIFIED ≥ €10" icon="€" value={nf(h.qualified_offers)} sub="Μόνο επαληθευμένες συμβάσεις" tone={Number(h.qualified_offers)?'positive':'negative'}/>
    </section>
    <div className={styles.twoGrid}>
     <Panel label="PRODUCT DISTRIBUTION" title="Μεγαλύτερες κατηγορίες">
      <EChart option={catalogChart} height={310} ariaLabel="Product category distribution"/>
     </Panel>
     <Panel label="MERCHANT COVERAGE" title="Μητρώο 334 προγραμμάτων">
      <div className={styles.barStack}>{(data.merchants||[]).map(x=><Bar key={x.status} label={short(x.status)} count={x.n} max={h.merchant_program_rows}/>)}</div>
      <div className={styles.divider}/>
      <div className={styles.researchCallout}><b>317 IDs απαιτούν επιβεβαίωση</b><p>Τα αρχικά merchant spreadsheets δεν αποδεικνύουν σωστά tracking links. Η ταυτοποίηση χρειάζεται επίσημο Linkwise program ID και ενεργή έγκριση.</p></div>
     </Panel>
     <Panel label="INGESTION RUNS" title="Ιστορικό feed επεξεργασίας" className={styles.span2}>
      <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>Started</th><th>Mode</th><th>Status</th><th>Scanned</th><th>Stored</th><th>Rejected</th><th>Reason</th></tr></thead><tbody>
      {runs.map(x=><tr key={x.id}><td>{dt(x.started_at)}</td><td>{x.mode||'legacy / unknown'}</td><td><Pill tone={scoreColor(x.state)}>{x.state}</Pill></td><td>{nf(x.scanned)}</td><td>{nf(x.stored)}</td><td>{nf(x.rejected)}</td><td>{x.error_code||'—'}</td></tr>)}
      </tbody></table>{runs.length===0&&<Empty text="Δεν υπάρχουν ολοκληρωμένα νέα delta runs."/ >}</div>
     </Panel>
    </div>
   </>}
   {tab==='intelligence'&&<>
    <section className={styles.kpiRow}>
     <Tile label="INDEXED DOCS" icon="▤" value={nf(h.searchable_docs)} sub="SQL/FTS retrieval"/>
     <Tile label="EMBEDDED" icon="◈" value={nf(h.vector_docs)} sub="multilingual-e5-small" tone={Number(h.vector_docs)?'positive':'caution'}/>
     <Tile label="GRAPH NODES" icon="◇" value={nf(h.graph_nodes)} sub="Provenance-linked entities"/>
     <Tile label="GRAPH RELATIONS" icon="⟷" value={nf(h.graph_edges)} sub={nf(h.graph_verified_edges)+' verified'} tone={Number(h.graph_verified_edges)?'positive':'caution'}/>
     <Tile label="RESEARCH BACKLOG" icon="⌕" value={nf((data.research||[]).reduce((s,x)=>s+Number(x.n||0),0))} sub="Greek demand/supply gaps"/>
    </section>
    <div className={styles.twoGrid}>
     <Panel label="HYBRID RETRIEVAL" title="Δοκίμασε πραγματική αναζήτηση" className={styles.span2}>
      <form className={styles.searchForm} onSubmit={doSearch}>
       <input aria-label="Semantic/SQL query" value={search} onChange={e=>setSearch(e.target.value)} maxLength={160} placeholder="π.χ. αισθητήρες υγρασίας, εξοικονόμηση ενέργειας, εργονομικό γραφείο…"/>
       <button type="submit" disabled={searching||search.trim().length<2}>{searching?'Searching…':'Search catalog ↗'}</button>
      </form>
      <div className={styles.searchMeta}>Real VMDB • Full-text SQL + future multilingual vectors • Candidates ≠ approved offers</div>
      {searchData&&<div className={styles.searchResults}>{(searchData.results||[]).slice(0,8).map((item,i)=><div className={styles.result} key={i}><div><b>{item.title}</b><small>{item.type} · {item.source_state} · rank {item.lexical_rank||'—'}</small></div><span>{nf(Number(item.score||0)*1000)} relevance</span></div>)}
      {searchData.results?.length===0&&<Empty text="Δεν εντοπίστηκε τεκμηριωμένο αποτέλεσμα με αυτόν τον όρο."/>}</div>}
     </Panel>
     <Panel label="EMBEDDING PIPELINE" title="Κατάσταση vector queue">
      <div className={styles.barStack}>{(data.embedding||[]).map(x=><Bar key={x.status} label={short(x.status)} count={x.n} max={h.searchable_docs} color={x.status==='ready'?'green':'blue'}/>)}</div>
      <small className={styles.note}>Η ύπαρξη vector index δεν σημαίνει ότι έχει τρέξει το μοντέλο. Τα 0 ready παραμένουν 0 μέχρι να λειτουργήσει ο E5 worker.</small>
     </Panel>
     <Panel label="MARKET RESEARCH" title="Evidence pipeline">
      <div className={styles.barStack}>{(data.research||[]).map(x=><Bar key={x.status} label={short(x.status)} count={x.n} max={41}/>)}</div>
      <p className={styles.note}>Απαιτούνται ανεξάρτητες ελληνικές πηγές για ζήτηση, ανταγωνισμό και αποθέματα. AI υποθέσεις δεν γίνονται αυτόματα verified.</p>
     </Panel>
    </div>
   </>}
   {tab==='operations'&&<>
    <div className={styles.twoGrid}>
     <Panel label="SAFE COMMANDS" title="Backend Controls">
      <div className={styles.controlList}><div><b>Search index sync</b><p>Ανανεώνει τις πηγές FTS από τις υπάρχουσες εγγραφές. Δεν εκτελεί embeddings.</p><button disabled={!!busy} onClick={()=>run('sync_search_docs')}>↻ Sync documents</button></div>
      <div><b>Research queue</b><p>Επαναδημιουργεί ελλείπουσες εργασίες για τα 334 προγράμματα, τα προϊόντα και τα pain gaps. Δεν καλεί πληρωμένο LLM.</p><button disabled={!!busy} onClick={()=>run('queue_research')}>＋ Queue missing tasks</button></div></div>
      <small className={styles.note}>Δεν διατίθεται κουμπί για μαζικό feed import, publishing, ανεξέλεγκτο SQL ή πληρωμές.</small>
     </Panel>
     <Panel label="AGENT OBJECTIVES" title="Pause / resume strategy">
      <div className={styles.objectives}>{goals.map(x=><div key={x.key}><div><b>{short(x.key)}</b><small>{x.purpose}</small></div><div><Pill tone={x.status==='active'?'positive':'caution'}>{x.status}</Pill><button disabled={!!busy} onClick={()=>run(x.status==='active'?'pause_objective':'resume_objective',x.key)}>{x.status==='active'?'Pause':'Resume'}</button></div></div>)}</div>
      <small className={styles.note}>Τα paused objectives εξαιρούνται πλέον από νέες αναθέσεις agents.</small>
     </Panel>
     <Panel label="AI RUN HISTORY" title="Πραγματικές εκτελέσεις agents">
      <div className={styles.tableScroll}><table className={styles.table}><thead><tr><th>Started</th><th>Runtime</th><th>Status</th><th>Tasks</th><th>Model calls</th></tr></thead><tbody>
      {agentRuns.map(r=><tr key={r.id}><td>{dt(r.started_at)}</td><td>{short(r.runtime_mode)}</td><td><Pill tone={scoreColor(r.state)}>{r.state}</Pill></td><td>{nf(r.processed_tasks)}</td><td>{nf(r.model_calls)}</td></tr>)}</tbody></table>
      {agentRuns.length===0&&<Empty text="Δεν υπάρχει τεκμηριωμένη παραγωγική εκτέλεση agent."/ >}</div>
     </Panel>
     <Panel label="AUDIT TRAIL" title="Καταγεγραμμένες ενέργειες">
      <div className={styles.auditList}>{(data.audit||[]).map(x=><div key={x.id}><span>{dt(x.created_at)}</span><b>{short(x.action)}</b><small>{x.target||'system'}</small></div>)}
      {(data.audit||[]).length===0&&<Empty text="Καμία ενέργεια από το νέο cockpit."/ >}</div>
     </Panel>
     <Panel label="RUNTIME CONFIGURATION" title="Πολιτικές backend και AI" className={styles.span2}>
      <div className={styles.configGrid}>{Object.entries(data.configuration||{}).map(([k,v])=><div key={k}><span>{short(k)}</span><strong>{typeof v==='boolean'?(v?'Enabled':'Disabled'):String(v)}</strong></div>)}</div>
      <div className={styles.policyBanner}>🛡 Οι αλλαγές σε εμπορική προμήθεια, model budgets και publisher eligibility δεν επιτρέπεται να παρακάμπτουν το verified €10 gate.</div>
     </Panel>
    </div>
   </>}
  </div>}
  <footer className={styles.footer}><span>◈ SOCIALMARKET // PRIVATE INTELLIGENCE CONSOLE</span><span>Supabase VMDB <i/> Fail-closed affiliate policy <i/> Greece</span></footer>
 </main>;
}
