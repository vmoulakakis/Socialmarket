'use client';

import dynamic from 'next/dynamic';

const Runtime=dynamic(()=>import('./EChartRuntime'),{
 ssr:false,
 loading:()=> <div role="status" aria-label="Loading analytical visualization" style={{width:'100%',height:420,display:'grid',placeItems:'center',color:'#64748b',fontSize:11}}>Loading analytical visualization…</div>
});

export default function EChart(props){return <Runtime {...props}/>}
