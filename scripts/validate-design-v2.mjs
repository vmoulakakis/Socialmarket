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
 [demand,'valid(x.demand_score)||valid(x.competition_score)||valid(x.opportunity_score)','selector includes evidence-backed rows even when opportunity is missing'],
 [engine,'canonical_metrics_read_only:true','canonical score immutability'],
 [engine,"status:reasons.length?'WITHHELD'",'neural history guard'],
 [skill,'Missing values remain missing','agent truth contract'],
 [skill,'Neural forecasts are WITHHELD','agent forecast contract'],
 [shell,"href:'/demand'",'Demand navigation']
];
for(const [text,needle,name] of checks){if(!text.includes(needle))errors.push(`Missing contract: ${name}`)}
for(const dep of ['echarts','@tanstack/react-table','motion']){if(!pkg.dependencies?.[dep])errors.push(`Missing dependency: ${dep}`)}


const workspaceCss=fs.readFileSync('components/CanonicalWorkspace.module.css','utf8');
const workspaceUi=fs.readFileSync('components/CanonicalWorkspace.jsx','utf8');
const appLayout=fs.readFileSync('app/layout.jsx','utf8');
const designDoc=fs.readFileSync('DESIGN.md','utf8');
for(const [value,name] of [
  ['PREMIUM WORKSPACE SAFETY PASS','scoped premium CSS marker'],
  [':focus-visible','visible keyboard focus'],
  ['@media(max-width:700px)','compact mobile rules'],
  ['@media(forced-colors:active)','forced-colors support'],
  ['@media(prefers-reduced-motion:reduce)','reduced-motion support']
])if(!workspaceCss.includes(value))errors.push('Missing workspace CSS contract: '+name);
for(const [value,name] of [
  ['workspace(section,{query,offset})','original canonical query and pagination'],
  ['rel="sponsored noopener noreferrer"','affiliate tracking link disclosure'],
  ['requestId.current','stale-request handling']
])if(!workspaceUi.includes(value))errors.push('Missing canonical workspace behavior: '+name);
if(!appLayout.includes("import './design-v2.css'"))errors.push('Canonical design tokens not loaded');
if(!designDoc.includes('Evidence-First Command Center'))errors.push('Design context not documented');
if(Array.from(workspaceCss).filter(c=>c==='{').length!==Array.from(workspaceCss).filter(c=>c==='}').length)errors.push('Workspace CSS braces are unbalanced');

if(errors.length){for(const e of errors)console.error(e);process.exit(1)}
console.log(`Design contract PASS: ${files.length} files and ${checks.length} V2/V3 presentation + truth contracts verified.`);
