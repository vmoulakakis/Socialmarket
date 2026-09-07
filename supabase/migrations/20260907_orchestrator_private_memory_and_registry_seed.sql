revoke all privileges on table public.orchestrator_runs from anon, authenticated;
revoke all privileges on table public.orchestrator_steps from anon, authenticated;
revoke all privileges on table public.site_registry from anon, authenticated;

insert into public.site_registry (id,project,production_url,repo,role,managed,index_policy,known_issues,updated_at) values
('socialmarket','socialmarket','https://socialmarket-theta.vercel.app','vmoulakakis/Socialmarket','control-plane',true,'private-admin','[]'::jsonb,now()),
('eu-local-day','socialmarket','https://socialmarket-theta.vercel.app/eu-local-day','vmoulakakis/Socialmarket','affiliate-funnel',true,'public','[]'::jsonb,now()),
('beatbot-sora-70','beatbot-sora-70-pool-savings','https://beatbot-sora-70-pool-savings-ayzopqxfi.vercel.app',null,'affiliate-funnel',false,null,'["orphan-source-linkage","x-robots-tag-noindex","affiliate-url-not-verified"]'::jsonb,now()),
('affiliateos','affiliateos','https://affiliateos-c0vinw5l1-vassilis-projects-3bf8541b.vercel.app',null,'affiliate-hub',false,null,'["orphan-source-linkage","api-refresh-timeout-60s"]'::jsonb,now()),
('myaffiliate','myaffiliate','https://myaffiliate-m8qr7vpmi-vassilis-projects-3bf8541b.vercel.app',null,'affiliate-hub',false,null,'["deployment-error","missing-public-output-directory","orphan-source-linkage"]'::jsonb,now()),
('dealora-ai','dealora-ai',null,'vmoulakakis/dealora-ai','commerce-app',false,null,'[]'::jsonb,now()),
('revolut-money-friction-scan','revolut-money-friction-scan',null,'vmoulakakis/revolut-money-friction-scan','tool',false,null,'[]'::jsonb,now()),
('travelai-greece','travelai_greece',null,'vmoulakakis/travelai_greece','travel',false,null,'[]'::jsonb,now()),
('xtool-ip919max-greece','xtool-ip919max-greece',null,null,'affiliate-funnel',false,null,'[]'::jsonb,now()),
('stairlift-pro-gr','stairlift-pro-gr',null,null,'affiliate-funnel',false,null,'[]'::jsonb,now()),
('agora-signal-greece','agora-signal-greece',null,null,'market-intelligence',false,null,'[]'::jsonb,now()),
('eu-solution-foundry','eu-solution-foundry',null,null,'commerce',false,null,'[]'::jsonb,now()),
('elite-deals-static-live','elite-deals-static-live',null,null,'affiliate-hub',false,null,'[]'::jsonb,now()),
('elite-deals-live','elite-deals-live',null,null,'affiliate-hub',false,null,'[]'::jsonb,now()),
('elite-deals-test','elite-deals-test',null,null,'test',false,null,'[]'::jsonb,now()),
('elite-deals-gr','elite-deals-gr',null,null,'affiliate-hub',false,null,'[]'::jsonb,now()),
('aigora','aigora',null,null,'market-intelligence',false,null,'[]'::jsonb,now()),
('travel-ai','travel-ai',null,null,'travel',false,null,'[]'::jsonb,now()),
('travel-ai-v27-live','travel-ai-v27-live',null,null,'travel',false,null,'[]'::jsonb,now())
on conflict (id) do update set
  project=excluded.project,
  production_url=excluded.production_url,
  repo=excluded.repo,
  role=excluded.role,
  managed=excluded.managed,
  index_policy=excluded.index_policy,
  known_issues=excluded.known_issues,
  updated_at=excluded.updated_at;
