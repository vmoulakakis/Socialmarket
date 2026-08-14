'use client';

import {useEffect,useState} from 'react';
import {supabase} from '@/lib/supabase';

export default function SitesPage(){
  const [sites,setSites]=useState([]);
  const [loading,setLoading]=useState(true);
  const [msg,setMsg]=useState('');

  async function load(){
    setLoading(true);
    const {data,error}=await supabase.from('brand_sites').select('*').order('name');
    if(error)setMsg(error.message); else setSites(data||[]);
    setLoading(false);
  }
  useEffect(()=>{load()},[]);

  async function toggle(site){
    const {error}=await supabase.from('brand_sites').update({active:!site.active,updated_at:new Date().toISOString()}).eq('id',site.id);
    if(error)setMsg(error.message); else await load();
  }

  return <main>
    <div className="hero"><div><div className="eyebrow">SINGLE SOURCE OF TRUTH</div><h1>Brands & Sites</h1><p className="sub">Όλα τα sites και brand streams ανήκουν εδώ. Το SocialMarket αποφασίζει strategy/content· το SocialScheduler λαμβάνει μόνο approved publishing jobs.</p></div></div>
    {msg?<div className="card"><b>{msg}</b></div>:null}
    {loading?<div className="muted">Loading…</div>:null}
    <div className="grid">
      {sites.map(site=><article className="card" key={site.id}>
        <div className="eyebrow">{site.slug}</div>
        <h2>{site.name}</h2>
        <p>{site.positioning||'—'}</p>
        {site.site_url?<p><a href={site.site_url} target="_blank" rel="noreferrer">Open site →</a></p>:<p className="muted">Brand stream χωρίς ξεχωριστό canonical site.</p>}
        <p className="muted"><b>CTA:</b> {site.primary_cta||'—'}</p>
        <div className="creative-meta"><span>{site.active?'Active':'Paused'}</span><span>{Array.isArray(site.content_pillars)?site.content_pillars.length:0} pillars</span></div>
        <button className="button" onClick={()=>toggle(site)}>{site.active?'Pause':'Activate'}</button>
      </article>)}
    </div>
  </main>;
}
