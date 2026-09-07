export const CAPABILITIES = [
  {id:'site.health',domain:'ops',risk:'low',requiresApproval:false,description:'Check HTTP availability, indexability and basic production health for registered sites.'},
  {id:'site.audit',domain:'growth',risk:'low',requiresApproval:false,description:'Audit SEO, conversion, tracking and runtime evidence before proposing changes.'},
  {id:'market.research',domain:'intelligence',risk:'low',requiresApproval:false,description:'Collect grounded demand, competition, pain-gap and product evidence.'},
  {id:'product.rank',domain:'intelligence',risk:'low',requiresApproval:false,description:'Rank only evidence-backed, commission-eligible products using canonical SocialMarket rules.'},
  {id:'affinity.design',domain:'build',risk:'low',requiresApproval:false,description:'Produce AFFINITY page/site architecture from audience, pain, offer and funnel intent.'},
  {id:'content.generate',domain:'growth',risk:'low',requiresApproval:false,description:'Generate evidence-grounded SEO, landing and lifecycle content.'},
  {id:'code.change',domain:'build',risk:'medium',requiresApproval:false,description:'Create bounded source-code changes in a Git-backed project and require tests before production.'},
  {id:'deploy.preview',domain:'deploy',risk:'medium',requiresApproval:false,description:'Create a preview deployment and verify it before promotion.'},
  {id:'deploy.production',domain:'deploy',risk:'medium',requiresApproval:false,description:'Promote a verified, reversible deployment to production.'},
  {id:'site.repair',domain:'ops',risk:'medium',requiresApproval:false,description:'Diagnose a failed site, apply a bounded repair, test, deploy and verify.'},
  {id:'experiment.run',domain:'growth',risk:'medium',requiresApproval:false,description:'Run bounded CRO/SEO experiments with measurable success criteria.'},
  {id:'email.bulk_send',domain:'outreach',risk:'high',requiresApproval:true,description:'Send a bulk campaign to external recipients.'},
  {id:'ads.spend',domain:'growth',risk:'high',requiresApproval:true,description:'Commit paid advertising budget.'},
  {id:'data.destructive',domain:'ops',risk:'critical',requiresApproval:true,description:'Delete or irreversibly mutate production data, domains or infrastructure.'},
  {id:'purchase.external',domain:'finance',risk:'critical',requiresApproval:true,description:'Purchase an external service or product.'}
];

export const CAPABILITY_MAP = Object.fromEntries(CAPABILITIES.map(x=>[x.id,x]));

export function capabilityPolicy(id){
  return CAPABILITY_MAP[id] ?? {id,risk:'critical',requiresApproval:true,description:'Unknown capability; fail closed.'};
}

export function safeCapabilityIds(){
  return CAPABILITIES.filter(x=>!x.requiresApproval).map(x=>x.id);
}
