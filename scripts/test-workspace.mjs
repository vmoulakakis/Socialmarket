import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const sql=readFileSync('supabase/migrations/20261016055701_canonical_workspace_read_api.sql','utf8');
assert.match(sql,/auth.uid\(\) is null/);
assert.match(sql,/revoke all on function public.socialmarket_workspace.*from public,anon/);
assert.match(sql,/security invoker/);
const pages=['products','forecast-products','creatives','scheduler','analytics','configuration','optimization'];
for(const page of pages){assert.match(readFileSync(`app/${page}/page.jsx`,'utf8'),/CanonicalWorkspace/);}
for(const page of ['merchants','niches']){assert.doesNotMatch(readFileSync(`app/${page}/page.jsx`,'utf8'),/supabase\.from/);}
const store=readFileSync('lib/orchestrator/store.js','utf8');
assert.match(store,/VMDB_SUPABASE_SERVICE_ROLE_KEY/);
assert.match(store,/SUPABASE_URL===APPROVED_SUPABASE_URL/);
console.log('Workspace route wiring, canonical credential isolation and SQL access contract passed.');
