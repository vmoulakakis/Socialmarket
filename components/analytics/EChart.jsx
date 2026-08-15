'use client';

import {useEffect,useRef} from 'react';
import * as echarts from 'echarts/core';
import {BarChart,FunnelChart,HeatmapChart,ScatterChart,TreemapChart} from 'echarts/charts';
import {GridComponent,MarkAreaComponent,TooltipComponent,VisualMapComponent} from 'echarts/components';
import {CanvasRenderer} from 'echarts/renderers';

echarts.use([BarChart,FunnelChart,HeatmapChart,ScatterChart,TreemapChart,GridComponent,MarkAreaComponent,TooltipComponent,VisualMapComponent,CanvasRenderer]);

export default function EChart({option,height=420,onEvents,ariaLabel='Interactive business intelligence chart'}){
 const ref=useRef(null);
 useEffect(()=>{
  if(!ref.current)return;
  const chart=echarts.init(ref.current,null,{renderer:'canvas'});
  chart.setOption(option,{notMerge:true,lazyUpdate:true});
  Object.entries(onEvents||{}).forEach(([name,handler])=>chart.on(name,handler));
  const ro=new ResizeObserver(()=>chart.resize());
  ro.observe(ref.current);
  return ()=>{ro.disconnect();chart.dispose()};
 },[option,onEvents]);
 return <div ref={ref} role="img" aria-label={ariaLabel} style={{width:'100%',height}}/>;
}
