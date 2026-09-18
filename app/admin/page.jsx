'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './admin.module.css';

const HEALTH_LABELS={
 active_merchants:'Active merchants',
 merchant360_assessed:'Merchant360 assessed',
 merchant360_ranked:'Merchant360 ranked',
 merchant_program_or_tracking_unverified:'Unverified programs/tracking',
 eligible_merchants:'Eligible merchants',
 problem_clusters:'Problem clusters',
 problem_demand_assessed:'Problems assessed',
 merchant_problem_fits:'Merchant/problem fits',
 eligible_product_offers:'Eligible offers',
 product_funnel_rows:'Product funnel rows',
 selected_products:'Selected products',
 semantic_documents_current:'Semantic documents',
 semantic_embeddings_pending:'Embeddings pending',
 semantic_embeddings_ready:'Embeddings ready',
 approved_social_presentations:'Approved social presentations',
 publishing_jobs_open:'Publishing jobs open',
 performance_feedback_events:'Performance feedback',
 agent_tool_tasks_open:'Agent tool tasks open',
};

const POLICY_FIELDS=[
 ['min_expected_commission_eur','Min expected commission €',0,500,1],
 ['min_demand_score','Min demand',0,100,1],
 ['max_competition_score','Max competition',0,100,1],
 ['min_supply_gap_score','Min supply gap',0,100,1],
 ['min_problem_solving_score','Min problem solving',0,100,1],
 ['min_trust_score','Min trust',0,100,1],
 ['min_price_value_score','Min price/value',0,100,1],
 ['min_greek_fulfilment_score','Min GR fulfilment',0,100,1],
 ['min_commercial_intent_score','Min commercial intent',0,100,1],
 ['min_greek_scarcity_score','Min Greek scarcity',0,100,1],
 ['min_confidence_adjusted_score','Min adjusted score',0,100,1],
 ['min_confidence','Min confidence',0,1,0.05],
 ['min_evidence_sources','Min evidence sources',0,20,1],
 ['max_merchants_per_category','Max merchants/category',1,100,1],
 ['max_merchants_per_subcategory','Max merchants/subcategory',1,100,1],
];

function num(v){return v===null||v===undefined||v===''?'':Number(v)}
function pct(v,max){if(!max)return 0;return Math.min(100,Math.round((Number(v||0)/Number(max))*100))}
function fmt(v){return Number(v||0).toLocaleString('el-GR')}

export default function AdminControlCenter(){
 const [data,setData]=useState(null);
 const [loading,setLoading]=useState(true);
 const [saving,setSaving]=useState('');
 const [error,setError]=useState('');
 const [message,setMessage]=useState('');
 const [tab,setTab]=useState('overview');
 const [policyDrafts,setPolicyDrafts]=useState({});
 const [budgetDrafts,setBudgetDrafts]=useState({});
 const [settingDrafts,setSettingDrafts]=useState({});

 async function load(){
  setLoading(true);setError('');
  const {data:payload,error:e}=await supabase.rpc('admin_socialmarket_control_snapshot');
  if(e){setError(e.message);setData(null)}
  else{
   setData(payload);
   setPolicyDrafts(Object.fromEntries((payload?.merchant_policies||[]).map(x=>[x.policy_key,{...x,weightsText:JSON.stringify(x.weights||{},null,2)}])));
   setBudgetDrafts(Object.fromEntries((payload?.budget_policies||[]).map(x=>[x.metric,{...x}])));
   setSettingDrafts(Object.fromEntries(Object.entries(payload?.app_settings||{}).map(([k,v])=>[k,JSON.stringify(v,null,2)])));
  }
  setLoading(false);
 }
 useEffect(()=>{load()},[]);

 const health=data?.health||{};
 const counts=health?.counts||{};
 const usage=useMemo(()=>Object.fromEntries((data?.budget_usage||[]).map(x=>[x.metric,x])),[data]);

 function patchPolicy(key,field,value){setPolicyDrafts(d=>({...d,[key]:{...d[key],[field]:value}}))}
 function patchBudget(key,field,value){setBudgetDrafts(d=>({...d,[key]:{...d[key],[field]:value}}))}

 async function savePolicy(key){
  setSaving('policy:'+key);setError('');setMessage('');
  try{
   const d=policyDrafts[key];let weights;
   try{weights=JSON.parse(d.weightsText||'{}')}catch{throw new Error('Invalid policy weights JSON')}
   const patch={enabled:Boolean(d.enabled),notes:d.notes||'',weights};
   for(const [field] of POLICY_FIELDS) patch[field]=num(d[field]);
   const {error:e}=await supabase.rpc('admin_update_merchant_policy',{p_policy_key:key,p_patch:patch});
   if(e)throw e;
   setMessage(`Saved merchant policy ${key}`);await load();
  }catch(e){setError(e.message||String(e))}finally{setSaving('')}
 }

 async function saveBudget(metric){
  setSaving('budget:'+metric);setError('');setMessage('');
  try{
   const d=budgetDrafts[metric];
   const {error:e}=await supabase.rpc('admin_update_budget_policy',{
    p_metric:metric,
    p_daily_limit:Number(d.daily_limit),
    p_monthly_limit:d.monthly_limit===''||d.monthly_limit===null?null:Number(d.monthly_limit),
    p_soft_threshold:Number(d.soft_threshold),
    p_enabled:Boolean(d.enabled),
   });
   if(e)throw e;
   setMessage(`Saved AI budget ${metric}`);await load();
  }catch(e){setError(e.message||String(e))}finally{setSaving('')}
 }

 async function saveSetting(key){
  setSaving('setting:'+key);setError('');setMessage('');
  try{
   let value;try{value=JSON.parse(settingDrafts[key]||'{}')}catch{throw new Error(`Invalid JSON for ${key}`)}
   const {error:e}=await supabase.rpc('admin_update_app_setting',{p_key:key,p_value:value});
   if(e)throw e;
   setMessage(`Saved runtime setting ${key}`);await load();
  }catch(e){setError(e.message||String(e))}finally{setSaving('')}
 }

 function addSetting(){
  const key=window.prompt('New setting key (lowercase, numbers, underscore)');
  if(!key)return;
  if(!/^[a-z0-9_]{2,80}$/.test(key)){setError('Invalid setting key');return}
  setSettingDrafts(d=>({...d,[key]:'{}'}));setTab('runtime');
 }

 if(loading)return <main className={styles.wrap}><div className={styles.loading}>Loading VMDB control plane…</div></main>;
 if(!data)return <main className={styles.wrap}><div className={styles.error}>{error||'Admin configuration unavailable'}</div></main>;

 const tabs=[['overview','Overview'],['merchants','Merchant Gates'],['budgets','AI Budgets'],['runtime','Runtime Settings'],['sites','Sites & Runtime'],['audit','Audit Log']];

 return <main className={styles.wrap}>
  <header className={styles.hero}>
   <div><span className={styles.eyebrow}>VMDB · CANONICAL ADMIN</span><h1>SocialMarket AI Control Center</h1><p>One place to inspect health, tune gates, control AI spend and manage runtime configuration without editing code.</p></div>
   <div className={styles.heroStatus}><span className={health.pipeline_status==='operational'?styles.good:styles.warn}>{health.pipeline_status||'unknown'}</span><b>{health.next_action||'—'}</b><small>Next canonical action</small></div>
  </header>

  <div className={styles.noticeRow}>
   {error&&<div className={styles.error}>{error}</div>}
   {message&&<div className={styles.success}>{message}</div>}
  </div>

  <nav className={styles.tabs}>{tabs.map(([id,label])=><button key={id} className={tab===id?styles.active:''} onClick={()=>setTab(id)}>{label}</button>)}</nav>

  {tab==='overview'&&<>
   <section className={styles.kpis}>
    {Object.entries(HEALTH_LABELS).map(([k,label])=><div className={styles.kpi} key={k}><span>{label}</span><strong>{fmt(counts[k])}</strong></div>)}
   </section>
   <section className={styles.grid2}>
    <div className={styles.panel}><span className={styles.eyebrow}>Pipeline</span><h2>Canonical state</h2>
     <div className={styles.statusList}><p><span>Database</span><b>{health.database||'vmdb'}</b></p><p><span>Backend</span><b>v{health.backend_version||'—'} · {health.backend_status||'—'}</b></p><p><span>Fail closed</span><b>{health.fail_closed?'Enabled':'Disabled'}</b></p><p><span>Pipeline</span><b>{health.pipeline_status||'—'}</b></p><p><span>Next action</span><b>{health.next_action||'—'}</b></p></div>
    </div>
    <div className={styles.panel}><span className={styles.eyebrow}>Readiness</span><h2>What is blocking production?</h2>
      <div className={styles.readiness}>
       <p><b>{counts.active_merchants||0}</b><span>active merchants</span></p>
       <p><b>{counts.eligible_merchants||0}</b><span>eligible merchants</span></p>
       <p><b>{counts.eligible_product_offers||0}</b><span>eligible offers</span></p>
       <p><b>{counts.selected_products||0}</b><span>selected products</span></p>
      </div>
      <p className={styles.help}>The system currently follows the VMDB health engine's next_action instead of weakening gates automatically.</p>
    </div>
   </section>
  </>}

  {tab==='merchants'&&<section className={styles.stack}>
   {(data.merchant_policies||[]).map(p=>{const d=policyDrafts[p.policy_key]||p;return <article className={styles.panel} key={p.policy_key}>
    <div className={styles.panelHead}><div><span className={styles.eyebrow}>MERCHANT POLICY</span><h2>{p.policy_key}</h2><p>{p.notes}</p></div><label className={styles.toggle}><input type="checkbox" checked={Boolean(d.enabled)} onChange={e=>patchPolicy(p.policy_key,'enabled',e.target.checked)}/><span>{d.enabled?'Enabled':'Disabled'}</span></label></div>
    <div className={styles.formGrid}>{POLICY_FIELDS.map(([field,label,min,max,step])=><label key={field}><span>{label}</span><input type="number" min={min} max={max} step={step} value={d[field]??''} onChange={e=>patchPolicy(p.policy_key,field,e.target.value===''?'':Number(e.target.value))}/></label>)}</div>
    <label className={styles.fullField}><span>Scoring / policy weights JSON</span><textarea rows="8" value={d.weightsText||''} onChange={e=>patchPolicy(p.policy_key,'weightsText',e.target.value)}/></label>
    <label className={styles.fullField}><span>Notes</span><textarea rows="3" value={d.notes||''} onChange={e=>patchPolicy(p.policy_key,'notes',e.target.value)}/></label>
    <div className={styles.actions}><button className={styles.primary} disabled={saving==='policy:'+p.policy_key} onClick={()=>savePolicy(p.policy_key)}>{saving==='policy:'+p.policy_key?'Saving…':'Save policy'}</button><small>Updated {new Date(p.updated_at).toLocaleString('el-GR')}</small></div>
   </article>})}
  </section>}

  {tab==='budgets'&&<section className={styles.cards}>
   {(data.budget_policies||[]).map(b=>{const d=budgetDrafts[b.metric]||b;const u=usage[b.metric]||{};return <article className={styles.panel} key={b.metric}>
    <div className={styles.panelHead}><div><span className={styles.eyebrow}>AI BUDGET</span><h2>{b.metric}</h2><p>{b.notes}</p></div><label className={styles.toggle}><input type="checkbox" checked={Boolean(d.enabled)} onChange={e=>patchBudget(b.metric,'enabled',e.target.checked)}/><span>{d.enabled?'On':'Off'}</span></label></div>
    <div className={styles.budgetBar}><i style={{width:`${pct(u.used_today,d.daily_limit)}%`}}/><span>{fmt(u.used_today)} / {fmt(d.daily_limit)} today</span></div>
    <div className={styles.formGrid}>
     <label><span>Daily limit</span><input type="number" min="1" value={d.daily_limit??''} onChange={e=>patchBudget(b.metric,'daily_limit',e.target.value)}/></label>
     <label><span>Monthly limit</span><input type="number" min="1" value={d.monthly_limit??''} onChange={e=>patchBudget(b.metric,'monthly_limit',e.target.value)}/></label>
     <label><span>Soft threshold</span><input type="number" min="0.05" max="1" step="0.05" value={d.soft_threshold??''} onChange={e=>patchBudget(b.metric,'soft_threshold',e.target.value)}/></label>
    </div>
    <div className={styles.actions}><button className={styles.primary} disabled={saving==='budget:'+b.metric} onClick={()=>saveBudget(b.metric)}>{saving==='budget:'+b.metric?'Saving…':'Save budget'}</button><small>{fmt(u.used_month)} used this month</small></div>
   </article>})}
  </section>}

  {tab==='runtime'&&<section className={styles.stack}>
   <div className={styles.sectionHead}><div><span className={styles.eyebrow}>RUNTIME JSON</span><h2>App settings</h2><p>Advanced settings are stored in VMDB and versioned through the audit trail.</p></div><button onClick={addSetting}>+ Add setting</button></div>
   {Object.keys(settingDrafts).sort().map(key=><article className={styles.panel} key={key}><div className={styles.panelHead}><div><span className={styles.eyebrow}>SETTING</span><h2>{key}</h2></div></div><textarea className={styles.code} rows="12" value={settingDrafts[key]} onChange={e=>setSettingDrafts(d=>({...d,[key]:e.target.value}))}/><div className={styles.actions}><button className={styles.primary} disabled={saving==='setting:'+key} onClick={()=>saveSetting(key)}>{saving==='setting:'+key?'Saving…':'Save JSON'}</button></div></article>)}
  </section>}

  {tab==='sites'&&<section className={styles.stack}>
   {(data.sites||[]).map(s=><article className={styles.site} key={s.id}><div><span className={styles.eyebrow}>{s.role||'site'}</span><h3>{s.id}</h3><p>{s.production_url||'No production URL'}</p></div><div className={styles.siteMeta}><span>{s.managed?'Managed':'Observed'}</span><b>{s.repo||'No repo linked'}</b><small>{(s.known_issues||[]).length} known issues</small></div></article>)}
  </section>}

  {tab==='audit'&&<section className={styles.panel}><div className={styles.panelHead}><div><span className={styles.eyebrow}>IMMUTABLE HISTORY</span><h2>Configuration audit</h2></div><button onClick={load}>Refresh</button></div><div className={styles.auditTable}>
   <div className={styles.auditRow+' '+styles.auditHead}><span>When</span><span>Domain</span><span>Key</span><span>Actor</span></div>
   {(data.audit||[]).map(a=><div className={styles.auditRow} key={a.id}><span>{new Date(a.created_at).toLocaleString('el-GR')}</span><span>{a.domain}</span><span>{a.config_key}</span><span>{a.actor_email}</span></div>)}
  </div></section>}

 </main>
}
