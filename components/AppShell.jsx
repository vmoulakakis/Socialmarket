'use client';

import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useMemo,useState} from 'react';

const groups=[
 {label:'Intelligence',items:[
  {href:'/analytics',label:'Overview',code:'OV'},
  {href:'/demand',label:'Demand',code:'DE'},
  {href:'/market',label:'Market Map',code:'MM'},
  {href:'/niches',label:'Pain Gaps',code:'PG'},
 ]},
 {label:'Affiliate',items:[
  {href:'/merchants',label:'Merchants',code:'ME'},
  {href:'/products',label:'Products',code:'PR'},
  {href:'/forecast-products',label:'Top Products',code:'TP'},
  {href:'/optimization',label:'Optimization',code:'OP'},
 ]},
 {label:'Execution',items:[
  {href:'/creatives',label:'Creatives',code:'CR'},
  {href:'/scheduler',label:'Publishing',code:'PB'},
 ]},
 {label:'System',items:[
  {href:'/',label:'AI Console',code:'AI'},
  {href:'/configuration',label:'Configuration',code:'CF'},
 ]},
];

function activePath(pathname,href){
 if(href==='/')return pathname==='/';
 return pathname===href||pathname.startsWith(`${href}/`);
}

export default function AppShell({children}){
 const pathname=usePathname();
 const [collapsed,setCollapsed]=useState(false);
 const context=useMemo(()=>{
  const item=groups.flatMap(g=>g.items).find(x=>activePath(pathname,x.href));
  return item?.label||'Intelligence';
 },[pathname]);
 return <div className={`smShell ${collapsed?'smShellCollapsed':''}`}>
  <aside className="smSidebar" aria-label="Primary navigation">
   <div className="smBrandRow">
    <Link href="/analytics" className="smBrand" aria-label="SocialMarket AI home"><span>SM</span><div><b>SocialMarket AI</b><small>Decision Intelligence</small></div></Link>
    <button className="smCollapse" onClick={()=>setCollapsed(v=>!v)} aria-label={collapsed?'Expand navigation':'Collapse navigation'}>{collapsed?'›':'‹'}</button>
   </div>
   <nav className="smNav">
    {groups.map(group=><section key={group.label} className="smNavGroup"><small>{group.label}</small>{group.items.map(item=><Link key={item.href} href={item.href} className={activePath(pathname,item.href)?'active':''} title={collapsed?item.label:undefined}><span className="smNavCode">{item.code}</span><b>{item.label}</b></Link>)}</section>)}
   </nav>
   <div className="smSideFoot"><span className="smLiveDot"/> <div><b>Production</b><small>Semantic truth preserved</small></div></div>
  </aside>
  <div className="smMain">
   <header className="smContextBar">
    <div className="smBreadcrumb"><span>SocialMarket</span><i>/</i><b>{context}</b><i>/</i><em>Greece</em></div>
    <div className="smContextMeta"><span className="smStatusChip"><i/>LIVE</span><span>Semantic Engine</span></div>
   </header>
   <div className="smContent">{children}</div>
  </div>
 </div>
}
