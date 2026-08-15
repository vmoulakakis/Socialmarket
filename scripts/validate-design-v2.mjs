import fs from 'node:fs';

const files=[
 'app/design-v2.css',
 'app/demand/page.jsx',
 'app/demand/demand.module.css',
 'components/AppShell.jsx',
 'components/analytics/EChart.jsx',
 'agents/skills/socialmarket-analytics-design/SKILL.md',
 'agents/skills/demand-intelligence-presentation/SKILL.md',
 'agents/skills/analytics-design-qa/SKILL.md',
 'agents/skills/demand-intelligence-v3/SKILL.md',
 'agents/skills/deep-demand-intelligence/SKILL.md',
 'agents/skills/greek-market-research/SKILL.md',
 'agents/skills/causal-demand-skeptic/SKILL.md',
 'agents/skills/kimi-business-analytics-storytelling/SKILL.md',
 'config/demand-intelligence-v3.json',
 'lib/demand-v3.js'
];

const errors=[];
for(const file of files){if(!fs.existsSync(file))errors.push(`Missing required file: ${file}`)}
const demand=fs.readFileSync('app/demand/page.jsx','utf8');
const engine=fs.readFileSync('lib/demand-v3.js','utf8');
const skill=fs.readFileSync('agents/skills/demand-intelligence-v3/SKILL.md','utf8');
const shell=fs.readFileSync('components/AppShell.jsx','utf8');
const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));

const checks=[
 [demand,"'/api/admin-dashboard'",'same-origin production snapshot'],
 [demand,"'/api/demand-intelligence'",'deep intelligence API'],
 [demand,'EChart','chart engine'],
 [demand,'AUDITABLE MARKET UNIVERSE','auditable canonical grid'],
 [demand,'PRODUCTION FORECAST','forecast guard'],
 [demand,'missing remains missing','missing-data UI contract'],
 [demand,'rows.filter(x=>x.taxonomy_id)','selector includes taxonomy rows even when opportunity is missing'],
 [demand,'Demand and supply are juxtaposed as separate dimensions','demand/supply presentation separation'],
 [demand,'CAUSAL SKEPTIC','causal skepticism scene'],
 [demand,'JOBS TO BE DONE','JTBD scene'],
 [engine,'canonical_metrics_read_only:true','canonical score immutability'],
 [engine,'demand_supply_separate:true','demand supply separation'],
 [engine,'correlation_is_not_causation:true','causal truth contract'],
 [engine,"status:reasons.length?'WITHHELD'",'neural history guard'],
 [engine,'canonical_demand_unchanged','fuzzy whitespace cannot modify demand'],
 [engine,'graph density is not demand','GraphRAG demand guard'],
 [skill,'Missing values remain missing','agent truth contract'],
 [skill,'Neural forecasts are WITHHELD','agent forecast contract'],
 [skill,'Correlation is never causation','agent causal contract'],
 [shell,"href:'/demand'",'Demand navigation']
];
for(const [text,needle,name] of checks){if(!text.includes(needle))errors.push(`Missing contract: ${name}`)}
for(const dep of ['echarts','@tanstack/react-table','motion']){if(!pkg.dependencies?.[dep])errors.push(`Missing dependency: ${dep}`)}

if(errors.length){for(const e of errors)console.error(e);process.exit(1)}
console.log(`Design contract PASS: ${files.length} files and ${checks.length} Deep Demand presentation + truth contracts verified.`);
