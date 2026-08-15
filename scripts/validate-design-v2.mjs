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
 [demand,'useReactTable','audit grid'],
 [demand,'FORECAST GATED','forecast guard'],
 [demand,'MISSING stays missing','missing-data UI contract'],
 [engine,'canonical_metrics_read_only:true','canonical score immutability'],
 [engine,"status:reasons.length?'WITHHELD'",'neural history guard'],
 [skill,'Missing values remain missing','agent truth contract'],
 [skill,'Neural forecasts are WITHHELD','agent forecast contract'],
 [shell,"href:'/demand'",'Demand navigation']
];
for(const [text,needle,name] of checks){if(!text.includes(needle))errors.push(`Missing contract: ${name}`)}
for(const dep of ['echarts','@tanstack/react-table','motion']){if(!pkg.dependencies?.[dep])errors.push(`Missing dependency: ${dep}`)}

if(errors.length){for(const e of errors)console.error(e);process.exit(1)}
console.log(`Design contract PASS: ${files.length} files and ${checks.length} V2/V3 presentation + truth contracts verified.`);
