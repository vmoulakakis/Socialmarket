import fs from 'node:fs';

const files=[
 'app/design-v2.css',
 'app/demand/page.jsx',
 'app/demand/demand.module.css',
 'components/AppShell.jsx',
 'components/analytics/EChart.jsx',
 'agents/skills/socialmarket-analytics-design/SKILL.md',
 'agents/skills/demand-intelligence-presentation/SKILL.md',
 'agents/skills/analytics-design-qa/SKILL.md'
];

const errors=[];
for(const file of files){if(!fs.existsSync(file))errors.push(`Missing required file: ${file}`)}
const demand=fs.readFileSync('app/demand/page.jsx','utf8');
const shell=fs.readFileSync('components/AppShell.jsx','utf8');
const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));

const checks=[
 [demand,'admin_dashboard_snapshot','production snapshot'],
 [demand,'EChart','chart engine'],
 [demand,'useReactTable','audit grid'],
 [demand,'Historical demand series is not exposed','historical-data guard'],
 [demand,'Sankey withheld','lineage guard'],
 [demand,'Missing ≠ zero','missing-data contract'],
 [shell,"href:'/demand'",'Demand navigation']
];
for(const [text,needle,name] of checks){if(!text.includes(needle))errors.push(`Missing contract: ${name}`)}
for(const dep of ['echarts','@tanstack/react-table','motion']){if(!pkg.dependencies?.[dep])errors.push(`Missing dependency: ${dep}`)}

if(errors.length){for(const e of errors)console.error(e);process.exit(1)}
console.log(`Design V2 contract PASS: ${files.length} files and ${checks.length} presentation contracts verified.`);
