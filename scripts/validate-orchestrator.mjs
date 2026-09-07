import fs from 'node:fs';

const requiredFiles=[
  'lib/orchestrator/capabilities.js',
  'lib/orchestrator/state-machine.js',
  'lib/orchestrator/store.js',
  'lib/orchestrator/runtime.js',
  'app/api/orchestrator/route.js',
  'data/site-registry.json',
  'supabase/migrations/20260907_autonomous_orchestrator.sql'
];
for(const file of requiredFiles){if(!fs.existsSync(file)) throw new Error(`Missing orchestrator contract file: ${file}`)}

const registry=JSON.parse(fs.readFileSync('data/site-registry.json','utf8'));
if(!Array.isArray(registry.sites)||registry.sites.length<5) throw new Error('Site registry must contain the discovered production estate.');
if(!registry.sites.some(x=>x.id==='socialmarket'&&x.role==='control-plane'&&x.repo)) throw new Error('SocialMarket must remain the Git-backed control plane.');

const caps=fs.readFileSync('lib/orchestrator/capabilities.js','utf8');
for(const gate of ['email.bulk_send','ads.spend','data.destructive','purchase.external']){
  const start=caps.indexOf(`id:'${gate}'`);
  if(start<0||!caps.slice(start,start+220).includes('requiresApproval:true')) throw new Error(`${gate} must remain approval-gated.`);
}

const runtime=fs.readFileSync('lib/orchestrator/runtime.js','utf8');
for(const contract of ['deterministicIntent','aiPlan','executeCapability','site.health','WAITING_APPROVAL','Unresolvable DAG dependencies']){
  if(!runtime.includes(contract)) throw new Error(`Runtime contract missing: ${contract}`);
}

console.log(`Orchestrator contract OK: ${registry.sites.length} registered projects/sites; irreversible actions fail closed.`);
