import {ImageResponse} from 'next/og';

export const runtime='edge';
export const alt='LuxeCorner — Curated Luxury Sofas';
export const size={width:1200,height:630};
export const contentType='image/png';

export default function Image(){
  return new ImageResponse(
    <div style={{width:'100%',height:'100%',display:'flex',position:'relative',background:'linear-gradient(135deg,#1c1915 0%,#4b4035 55%,#b8a58d 100%)',color:'#f8f3ea',fontFamily:'Georgia,serif',padding:'68px'}}>
      <div style={{position:'absolute',inset:'22px',border:'1px solid rgba(255,255,255,.28)'}}/>
      <div style={{display:'flex',flexDirection:'column',justifyContent:'space-between',width:'100%'}}>
        <div style={{display:'flex',justifyContent:'space-between',fontFamily:'Arial,sans-serif',fontSize:18,letterSpacing:5,textTransform:'uppercase'}}>
          <span>LUXECORNER</span><span>CURATED LIVING</span>
        </div>
        <div style={{display:'flex',flexDirection:'column',maxWidth:940}}>
          <div style={{fontFamily:'Arial,sans-serif',fontSize:18,letterSpacing:5,textTransform:'uppercase',opacity:.75,marginBottom:22}}>THE PREMIUM SOFA EDIT</div>
          <div style={{fontSize:82,lineHeight:.96,letterSpacing:-2}}>The sofa that changes<br/>the whole room.</div>
        </div>
        <div style={{fontFamily:'Arial,sans-serif',fontSize:19,opacity:.76}}>Statement corners · Velvet icons · Soft luxury · Sofa beds</div>
      </div>
    </div>,
    size
  );
}
