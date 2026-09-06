import fs from 'node:fs';

const requiredFiles = [
  'skills/AFFINITY_SKILL.md',
  'skills/AFFINITY_PAGE_ENGINE.md',
  'config/affinity-page-engine.json',
  'agents/skills/affinity-creative-production/SKILL.md',
  'agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md',
  'agents/skills/affinity-creative-production/PAGE_DNA.schema.json',
  'agents/skills/affinity-creative-production/PROMPT_CONTRACTS.md',
  'agents/skills/affinity-creative-production/QA_GATES.md',
  'agents/skills/affinity-creative-production/BUILD_HANDOFF.schema.json',
  'agents/skills/affinity-creative-production/EXPERIMENT.schema.json',
  'data/affinity-page-engine-example.json',
  'agents/skills/growth-orchestrator/SKILL.md',
  'projects/socialmarket-growthops/README.md'
];

const errors = [];
for (const file of requiredFiles) {
  if (!fs.existsSync(file)) errors.push(`Missing required file: ${file}`);
}

function read(file) {
  return fs.readFileSync(file, 'utf8');
}

function parseJson(file) {
  try {
    return JSON.parse(read(file));
  } catch (error) {
    errors.push(`Invalid JSON in ${file}: ${error.message}`);
    return null;
  }
}

const config = parseJson('config/affinity-page-engine.json');
const pageSchema = parseJson('agents/skills/affinity-creative-production/PAGE_DNA.schema.json');
const buildSchema = parseJson('agents/skills/affinity-creative-production/BUILD_HANDOFF.schema.json');
const experimentSchema = parseJson('agents/skills/affinity-creative-production/EXPERIMENT.schema.json');
const fixture = parseJson('data/affinity-page-engine-example.json');

const affinity = read('skills/AFFINITY_SKILL.md');
const engine = read('skills/AFFINITY_PAGE_ENGINE.md');
const creative = read('agents/skills/affinity-creative-production/SKILL.md');
const registry = read('agents/skills/affinity-creative-production/COMPONENT_REGISTRY.md');
const prompts = read('agents/skills/affinity-creative-production/PROMPT_CONTRACTS.md');
const qa = read('agents/skills/affinity-creative-production/QA_GATES.md');
const orchestrator = read('agents/skills/growth-orchestrator/SKILL.md');
const growthOps = read('projects/socialmarket-growthops/README.md');

const mandatoryPipeline = [
  'source_ingest',
  'context_brief',
  'brand_store_dna',
  'decision_barriers',
  'angle_matrix',
  'message_match',
  'archetype',
  'layout_dna',
  'page_dna',
  'component_plan',
  'copy',
  'media',
  'design_tokens',
  'assembly',
  'responsive_qa',
  'conversion_layer',
  'localization',
  'variants',
  'publish',
  'measure',
  'learn'
];

if (config) {
  for (const stage of mandatoryPipeline) {
    if (!config.pipeline?.includes(stage)) errors.push(`Pipeline missing stage: ${stage}`);
  }
  if (!config.brand_store_dna?.required_fields?.includes('brand_voice')) errors.push('Brand/Store DNA contract missing brand_voice');
  if (!config.layout_dna?.persistent) errors.push('Layout DNA must be persistent/versionable');
  if (config.component_scoring?.minimum_recommended_score !== 70) errors.push('Component score threshold must remain 70');
  if (config.qa_score?.minimum !== 85) errors.push('QA minimum must remain 85');
  if (config.performance?.field_good_targets?.lcp_ms_max !== 2500) errors.push('LCP target must be 2500ms');
  if (config.performance?.field_good_targets?.inp_ms_max !== 200) errors.push('INP target must be 200ms');
  if (config.performance?.field_good_targets?.cls_max !== 0.1) errors.push('CLS target must be 0.1');
  if (config.accessibility?.target !== 'WCAG_2_2_AA') errors.push('Accessibility target must be WCAG 2.2 AA');
}

function validateTopRequired(schema, object, label) {
  if (!schema || !object) return;
  for (const key of schema.required ?? []) {
    if (!(key in object)) errors.push(`${label} missing required property: ${key}`);
  }
}

validateTopRequired(pageSchema, fixture, 'Page DNA fixture');

if (fixture) {
  if (!Array.isArray(fixture.sections) || fixture.sections.length < 1) errors.push('Fixture must contain sections');
  if (fixture.qa?.minimum_score !== 85) errors.push('Fixture QA minimum must be 85');
  if (fixture.analytics?.primary_metric !== 'RPV') errors.push('Fixture primary metric must be RPV');
}

for (const [schema, name] of [
  [pageSchema, 'Page DNA schema'],
  [buildSchema, 'Build Handoff schema'],
  [experimentSchema, 'Experiment schema']
]) {
  if (schema?.$schema !== 'https://json-schema.org/draft/2020-12/schema') errors.push(`${name} must use JSON Schema 2020-12`);
}

const registryIds = [];
for (const line of registry.split('\n')) {
  const match = line.match(/^\|\s*([A-Z][A-Z0-9-]+)\s*\|/);
  if (match && match[1] !== 'ID') registryIds.push(match[1]);
}
const duplicates = registryIds.filter((id, index) => registryIds.indexOf(id) !== index);
if (duplicates.length) errors.push(`Duplicate component IDs: ${[...new Set(duplicates)].join(', ')}`);
if (registryIds.length < 80) errors.push(`Component registry unexpectedly small: ${registryIds.length} IDs; expected >=80`);

if (fixture) {
  for (const section of fixture.sections ?? []) {
    if (!registryIds.includes(section.component_id)) errors.push(`Fixture references unknown component ID: ${section.component_id}`);
  }
}

const contractChecks = [
  [affinity, 'AFFINITY_PAGE_ENGINE.md', 'AFFINITY core Page Engine dependency'],
  [affinity, 'PAGE_DNA.schema.json', 'AFFINITY core Page DNA dependency'],
  [engine, 'COMPONENT_REGISTRY.md', 'Page Engine component registry dependency'],
  [creative, 'PAGE_DNA.schema.json', 'Creative Page DNA dependency'],
  [prompts, 'DECISION-BARRIER AGENT', 'Decision barrier prompt stage'],
  [prompts, 'BRAND / STORE DNA AGENT', 'Brand/Store DNA prompt stage'],
  [prompts, 'LAYOUT DNA AGENT', 'Layout DNA prompt stage'],
  [prompts, 'COMPONENT PLANNER / SCORER', 'Component scorer prompt stage'],
  [qa, 'WCAG 2.2 AA', 'Accessibility QA contract'],
  [qa, 'LCP ≤ 2.5 s', 'LCP QA contract'],
  [qa, 'Variant-isolation gate', 'Experiment isolation QA contract'],
  [orchestrator, 'AFFINITY Creative Production Agent', 'Orchestrator page agent routing'],
  [orchestrator, 'Page DNA', 'Orchestrator Page DNA routing'],
  [growthOps, 'AFFINITY Page Engine', 'GrowthOps Page Engine canonical dependency']
];

for (const [text, needle, name] of contractChecks) {
  if (!text.includes(needle)) errors.push(`Missing contract: ${name}`);
}

if (errors.length) {
  for (const error of errors) console.error(error);
  process.exit(1);
}

console.log(`AFFINITY Page Engine PASS: ${requiredFiles.length} required files, ${registryIds.length} component IDs, pipeline/config/schema/fixture/orchestration contracts verified.`);
