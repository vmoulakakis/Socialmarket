const clamp=n=>Math.max(0,Math.min(100,n));
export function calculateHigo(i){
  const reasons=[];
  if(i.price<150) reasons.push('Price below EUR 150 gate');
  if(!i.inStock) reasons.push('Out of stock');
  if(!i.trackingUrlValid) reasons.push('Invalid tracking URL');
  if(!i.imageValid) reasons.push('No usable product image');
  const frictionLimit=i.discountPercent>=40?.75:i.discountPercent>=30?.6:.4;
  if(i.purchaseFriction>frictionLimit) reasons.push(`Purchase friction ${i.purchaseFriction.toFixed(2)} exceeds ${frictionLimit.toFixed(2)}`);
  const eligible=reasons.length===0;
  const raw=clamp(i.currentDemand*.25+i.forecastMomentum*.20+i.attentionGap*.20+i.purchaseEase*.10+i.priceDiscount*.10+i.evidenceQuality*.05+i.offerReliability*.05+i.creativePotential*.05);
  const score=eligible?clamp(raw*(clamp(i.confidence)/100)):0;
  const decision=score>=92?'PRIORITY':score>=85?'CREATE_CREATIVE':score>=75?'WATCHLIST':score>=60?'MONITOR':'DROP';
  return {eligible,raw:+raw.toFixed(1),score:+score.toFixed(1),decision,reasons};
}
