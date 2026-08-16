'use client';

import {useEffect,useMemo,useState} from 'react';
import {supabase} from '@/lib/supabase';
import styles from './creatives.module.css';

const arr=v=>Array.isArray(v)?v:[];
const obj=v=>v&&typeof v==='object'&&!Array.isArray(v)?v:{};
const num=(v,d=1)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('el-GR',{maximumFractionDigits:d});
const money=v=>v===null||v===undefined?'—':`€${Number(v).toLocaleString('el-GR',{minimumFractionDigits:2,maximumFractionDigits:2})}`;

function CreativePreview({row,variant}){
  return <div className={`${styles.preview} ${variant?.id==='reel_9x16'?styles.vertical:variant?.id==='square_1x1'?styles.square:styles.feed}`}>
    {row.image_url?<img src={row.image_url} alt={row.product_name||'Product'}/>:<div className={styles.noImage}>NO IMAGE</div>}
    <div className={styles.previewShade}/><div className={styles.previewCopy}><span>#{row.global_rank} · {row.brand_name||row.merchant_name}</span><strong>{variant?.headline||row.promotion_angle||row.product_name}</strong>{variant?.subheadline&&<p>{variant.subheadline}</p>}<b>{variant?.cta||'Δες το προϊόν'}</b></div>
    <div className={styles.qrZone}>QR<br/><small>exact link</small></div>
  </div>
}

export default function Creatives(){
  const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState('');
  async function load(){setLoading(true);setError('');const {data,error}=await supabase.rpc('admin_top20_creative_products');if(error)setError(error.message);else setRows(data||[]);setLoading(false)}
  useEffect(()=>{load()},[]);
  const stats=useMemo(()=>({generated:rows.filter(x=>Object.keys(obj(x.creative_pack)).length).length,ready:rows.filter(x=>x.creative_status==='ready').length,review:rows.filter(x=>x.creative_status==='needs_review').length}),[rows]);
  return <main className={styles.page}>
    <header className={styles.hero}><div><span className={styles.eyebrow}>SOCIALMARKET · TOP-20 CAMPAIGN LAB</span><h1>Creatives για τα προϊόντα που αξίζουν πρώτα</h1><p>Ranking → SEO → Creative Director → Creative Skeptic. Τρία campaign variants ανά Top‑20 προϊόν, πάντα πάνω στην πραγματική εικόνα και στο ακριβές affiliate tracking URL.</p></div><div className={styles.actions}><a href="/forecast-products">Products →</a><button onClick={load}>↻ Refresh</button></div></header>
    {error&&<div className={styles.error}>{error}</div>}
    <section className={styles.kpis}><div><span>Top products</span><b>{rows.length}/20</b></div><div><span>Creative packs</span><b>{stats.generated}/20</b></div><div><span>Audit ready</span><b>{stats.ready}</b></div><div><span>Needs review</span><b>{stats.review}</b></div></section>
    {loading?<div className={styles.loading}>Loading Top‑20 campaign packs…</div>:rows.length===0?<section className={styles.empty}><h2>Το final ranking δεν έχει ολοκληρωθεί ακόμη.</h2><p>Η παραγωγική έκδοση δεν δηλώνει success πριν υπάρχουν τουλάχιστον 100 ranked προϊόντα και creative packs για τα Top‑20.</p></section>:<section className={styles.list}>{rows.map(row=>{const pack=obj(row.creative_pack),audit=obj(row.creative_audit),variants=arr(pack.variants);return <article className={styles.card} key={`${row.run_id}-${row.source_record_hash}`}>
      <div className={styles.cardHead}><div><span className={styles.rank}>#{row.global_rank}</span><div><h2>{row.product_name}</h2><p>{row.merchant_name}{row.brand_name?` · ${row.brand_name}`:''} · {money(row.effective_price)} · commission {money(row.expected_commission_eur)}</p></div></div><div className={`${styles.status} ${row.creative_status==='ready'?styles.ready:styles.review}`}>{row.creative_status==='ready'?'READY':'REVIEW'}</div></div>
      <div className={styles.strategy}><div><span>Campaign theme</span><b>{pack.campaign_theme||'—'}</b></div><div><span>Emotional angle</span><b>{pack.emotional_angle||'—'}</b></div><div><span>Audience</span><b>{pack.audience||row.audience||'—'}</b></div><div><span>Rank score</span><b>{num(row.rank_score,1)}</b></div></div>
      <div className={styles.variantGrid}>{variants.map((v,i)=><section className={styles.variant} key={v.id||i}><CreativePreview row={row} variant={v}/><div className={styles.variantBody}><div className={styles.variantTitle}><b>{v.id||`Variant ${i+1}`}</b><span>{arr(v.platform).join(' · ')} · {v.aspect_ratio||'—'}</span></div><p className={styles.hook}>{v.hook||'—'}</p><dl><dt>CTA</dt><dd>{v.cta||'—'}</dd><dt>Visual</dt><dd>{v.visual_direction||'—'}</dd><dt>Composition</dt><dd>{v.composition||'—'}</dd><dt>QR</dt><dd>{obj(v.qr_spec).placement||'—'} · exact tracking URL</dd></dl><details><summary>Copy, hashtags & storyboard</summary><p>{v.caption||'—'}</p><div className={styles.tags}>{arr(v.hashtags).map(h=><span key={h}>{h}</span>)}</div>{arr(v.reel_storyboard).length>0&&<ol>{arr(v.reel_storyboard).map((s,idx)=><li key={idx}>{typeof s==='object'?JSON.stringify(s):String(s)}</li>)}</ol>}</details></div></section>)}</div>
      <div className={styles.audit}><div><b>Creative Skeptic</b><span>Risk {num(audit.risk_score,0)}/100</span></div><p>{audit.audit_summary||'Audit pending.'}</p>{arr(audit.unsupported_claims).length>0&&<p><strong>Unsupported:</strong> {arr(audit.unsupported_claims).join(' · ')}</p>}{arr(audit.corrections).length>0&&<p><strong>Corrections:</strong> {arr(audit.corrections).join(' · ')}</p>}</div>
      <footer className={styles.cardFooter}><span>{row.promotion_angle||row.promotion_reason||''}</span>{row.tracking_url&&<a href={row.tracking_url} target="_blank" rel="noreferrer">Exact affiliate URL ↗</a>}</footer>
    </article>})}</section>}
  </main>
}
