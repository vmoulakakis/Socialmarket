const clamp=n=>Math.max(0,Math.min(100,Number(n)||0));
const runwayScore=days=>days==null||days<=20?0:days<=30?40:days<=60?65:days<=90?85:100;

export function calculateHigo(i){
  const reasons=[];
  const days=Number(i.validityDaysRemaining);
  const runway=runwayScore(Number.isFinite(days)?days:null);
  const sellerCompetition=clamp(i.sellerCompetition);
  const adPressure=clamp(i.adPressureProxy);
  const adConfidence=Math.max(0,Math.min(1,Number(i.adPressureConfidence)||0));
  const competitionKill=sellerCompetition>=82||(adPressure>=92&&adConfidence>=0.65);

  if(Number(i.price)<150) reasons.push('Price below EUR 150 gate');
  if(!Number.isFinite(days)||days<=20) reasons.push('valid_to must be more than 20 days from today');
  if(i.travelRelated) reasons.push('Travel / travel-goods category excluded');
  if(i.inStock===false) reasons.push('Out of stock');
  if(!i.trackingUrlValid) reasons.push('Invalid tracking URL');
  if(!i.imageValid) reasons.push('No usable product image');
  if(competitionKill) reasons.push(sellerCompetition>=82?'Seller competition kill':'Ad-pressure proxy kill');

  const discount=Number(i.discountPercent)||0;
  const friction=Number(i.purchaseFriction)||0;
  const frictionLimit=discount>=45?.75:discount>=30?.6:.4;
  if(friction>frictionLimit) reasons.push(`Purchase friction ${friction.toFixed(2)} exceeds ${frictionLimit.toFixed(2)}`);

  const eligible=reasons.length===0;
  const raw=clamp(
    clamp(i.currentDemand)*.24+
    clamp(i.forecastMomentum)*.18+
    clamp(i.attentionGap)*.20+
    clamp(i.purchaseEase)*.10+
    clamp(i.priceDiscount)*.08+
    runway*.08+
    clamp(i.evidenceQuality)*.05+
    clamp(i.offerReliability)*.04+
    clamp(i.creativePotential)*.03
  );
  const confidence=Math.max(0,Math.min(1,Number(i.confidence)>1?Number(i.confidence)/100:Number(i.confidence)||0));
  const score=eligible?clamp(raw-(1-confidence)*20):0;
  const decision=!eligible?'DROP':score>=92?'PRIORITY':score>=85?'CREATE_CREATIVE':score>=75?'WATCHLIST':score>=60?'MONITOR':'DROP';
  return {eligible,raw:+raw.toFixed(1),score:+score.toFixed(1),decision,validityRunwayScore:runway,competitionKill,reasons};
}
