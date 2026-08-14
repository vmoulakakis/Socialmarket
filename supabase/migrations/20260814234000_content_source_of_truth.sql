-- SocialMarket owns brand/content intelligence. SocialScheduler only executes approved outbox jobs.

create table if not exists public.brand_sites (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  site_url text,
  positioning text,
  target_audience text,
  primary_cta text,
  content_pillars jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_items (
  id uuid primary key default gen_random_uuid(),
  source_key text unique,
  brand_site_id uuid not null references public.brand_sites(id) on delete restrict,
  product_id uuid references public.products(id) on delete set null,
  opportunity_score_id uuid references public.opportunity_scores(id) on delete set null,
  creative_asset_id uuid references public.creative_assets(id) on delete set null,
  title text not null,
  angle text,
  core_copy text,
  cta text,
  tracking_url text,
  media_url text,
  status text not null default 'draft' check (status in ('draft','approved','rejected','queued','completed','cancelled')),
  scheduled_from timestamptz,
  approved_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.publishing_outbox (
  id uuid primary key default gen_random_uuid(),
  content_item_id uuid not null references public.content_items(id) on delete cascade,
  platform text not null check (platform in ('facebook','instagram','tiktok')),
  caption text not null,
  hashtags text[] not null default '{}'::text[],
  format text not null default 'post',
  media_url text,
  tracking_url text,
  scheduled_for timestamptz,
  priority smallint not null default 50,
  status text not null default 'approved' check (status in ('approved','leased','scheduled','published','failed','cancelled')),
  claimed_by text,
  claimed_at timestamptz,
  lease_expires_at timestamptz,
  external_post_id text,
  external_permalink text,
  published_at timestamptz,
  attempt_count integer not null default 0,
  last_error text,
  executor_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(content_item_id, platform)
);

create index if not exists idx_content_items_brand_status on public.content_items(brand_site_id, status, created_at desc);
create index if not exists idx_publishing_outbox_claim on public.publishing_outbox(status, scheduled_for, priority desc);
create index if not exists idx_publishing_outbox_external on public.publishing_outbox(external_post_id) where external_post_id is not null;

alter table public.brand_sites enable row level security;
alter table public.content_items enable row level security;
alter table public.publishing_outbox enable row level security;

drop policy if exists admin_authenticated_all on public.brand_sites;
create policy admin_authenticated_all on public.brand_sites for all to authenticated using (true) with check (true);
drop policy if exists admin_authenticated_all on public.content_items;
create policy admin_authenticated_all on public.content_items for all to authenticated using (true) with check (true);
drop policy if exists admin_authenticated_all on public.publishing_outbox;
create policy admin_authenticated_all on public.publishing_outbox for all to authenticated using (true) with check (true);

insert into public.brand_sites(slug,name,site_url,positioning,primary_cta,content_pillars,metadata) values
('coffeego-ai','CoffeeGo AI','https://coffeego-ai.vmoulakakis.chatgpt.site/','AI guide for portable espresso and coffee setup selection','Smart Match / ask Elena','["portable espresso education","setup comparison","coffee economics","AI advisor","honest buying guidance"]'::jsonb,'{"legacy_scheduler_brand":"CoffeeGo / Coffee Anywhere AI"}'::jsonb),
('cabinpilot-travel','CabinPilot Travel','https://cabinpilot-travel.vmoulakakis.chatgpt.site/','Cabin luggage and airline-rule decision support','Check cabin fit before travel','["airline rules","luggage dimensions","packing","fee avoidance","travel stress reduction"]'::jsonb,'{"legacy_scheduler_brand":"CabinPilot Travel"}'::jsonb),
('cabinpilot-smart-savings','CabinPilot Smart Savings',null,'Crew and frequent-traveller savings/value stream','Compare real annual travel benefit','["crew benefits","travel savings","benefit calculators","frequent traveller value"]'::jsonb,'{"legacy_scheduler_brand":"CabinPilot Smart Savings"}'::jsonb),
('lyseis-pou-axizoun','Λύσεις που Αξίζουν / Biz Box Solver','https://lyseis-pou-axizoun.vmoulakakis.chatgpt.site/','Practical value solutions, tools and offers without hype','See if the solution is worth it','["practical savings","business tools","ecommerce","pain-point solving","worth-it analysis"]'::jsonb,'{"legacy_scheduler_brand":"Lyseis / Biz Box Solver"}'::jsonb),
('travel-ai','Travel AI / GreekVibes','https://travel-ai-navy-eight.vercel.app/','Greek AI travel discovery and advisor','Find the next Greek escape','["destination discovery","seasonal Greece","weekend escapes","travel preferences","offers and ideas"]'::jsonb,'{"legacy_scheduler_brand":"Travel AI / GreekVibes"}'::jsonb),
('red-raven-eyewear','Red Raven Eyewear','https://red-raven-eyewear-handcrafted-sunglasses-122630476133.europe-west1.run.app/','Eyewear and handcrafted sunglasses brand stream','Explore verified eyewear','["eyewear education","style","verified product features","seasonal sun protection"]'::jsonb,'{"legacy_scheduler_brand":"Red Raven Eyewear"}'::jsonb)
on conflict (slug) do update set
  name=excluded.name,
  site_url=excluded.site_url,
  positioning=excluded.positioning,
  primary_cta=excluded.primary_cta,
  content_pillars=excluded.content_pillars,
  metadata=public.brand_sites.metadata || excluded.metadata,
  active=true,
  updated_at=now();

create or replace function public.queue_content_item(
  p_content_item_id uuid,
  p_platform_payloads jsonb,
  p_default_scheduled_for timestamptz default null
) returns setof public.publishing_outbox
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_platform text;
  v_payload jsonb;
  v_item public.content_items%rowtype;
begin
  select * into v_item from public.content_items where id = p_content_item_id for update;
  if not found then raise exception 'content item not found'; end if;
  if v_item.status <> 'approved' then raise exception 'content item must be approved before queueing'; end if;

  for v_platform, v_payload in select key, value from jsonb_each(coalesce(p_platform_payloads,'{}'::jsonb)) loop
    if v_platform not in ('facebook','instagram','tiktok') then
      raise exception 'unsupported platform: %', v_platform;
    end if;
    if coalesce(trim(v_payload->>'caption'),'') = '' then
      raise exception 'caption is required for %', v_platform;
    end if;

    insert into public.publishing_outbox(
      content_item_id, platform, caption, hashtags, format, media_url, tracking_url, scheduled_for, priority, status, updated_at
    ) values (
      p_content_item_id,
      v_platform,
      v_payload->>'caption',
      coalesce(array(select jsonb_array_elements_text(coalesce(v_payload->'hashtags','[]'::jsonb))), '{}'::text[]),
      coalesce(nullif(v_payload->>'format',''),'post'),
      coalesce(nullif(v_payload->>'media_url',''),v_item.media_url),
      coalesce(nullif(v_payload->>'tracking_url',''),v_item.tracking_url),
      coalesce((v_payload->>'scheduled_for')::timestamptz,p_default_scheduled_for,v_item.scheduled_from),
      coalesce((v_payload->>'priority')::smallint,50),
      'approved',
      now()
    )
    on conflict(content_item_id, platform) do update set
      caption=excluded.caption,
      hashtags=excluded.hashtags,
      format=excluded.format,
      media_url=excluded.media_url,
      tracking_url=excluded.tracking_url,
      scheduled_for=excluded.scheduled_for,
      priority=excluded.priority,
      status=case when public.publishing_outbox.status in ('published','scheduled') then public.publishing_outbox.status else 'approved' end,
      last_error=null,
      updated_at=now();
  end loop;

  update public.content_items set status='queued', updated_at=now() where id=p_content_item_id;
  return query select * from public.publishing_outbox where content_item_id=p_content_item_id order by platform;
end;
$$;

grant execute on function public.queue_content_item(uuid,jsonb,timestamptz) to authenticated;

create or replace function public.claim_publishing_jobs(
  p_executor text,
  p_limit integer default 10,
  p_lease_minutes integer default 30
) returns table(
  id uuid,
  content_item_id uuid,
  platform text,
  caption text,
  hashtags text[],
  format text,
  media_url text,
  tracking_url text,
  scheduled_for timestamptz,
  priority smallint,
  brand_slug text,
  brand_name text,
  title text
)
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with picked as (
    select o.id
    from public.publishing_outbox o
    where o.status='approved'
       or (o.status='leased' and coalesce(o.lease_expires_at,now()-interval '1 second') < now())
    order by coalesce(o.scheduled_for, now()+interval '365 days'), o.priority desc, o.created_at
    for update skip locked
    limit greatest(1,least(coalesce(p_limit,10),50))
  ), leased as (
    update public.publishing_outbox o
       set status='leased', claimed_by=p_executor, claimed_at=now(),
           lease_expires_at=now()+make_interval(mins => greatest(5,least(coalesce(p_lease_minutes,30),120))),
           attempt_count=o.attempt_count+1, updated_at=now()
     where o.id in (select picked.id from picked)
     returning o.*
  )
  select l.id,l.content_item_id,l.platform,l.caption,l.hashtags,l.format,l.media_url,l.tracking_url,
         l.scheduled_for,l.priority,b.slug,b.name,c.title
    from leased l
    join public.content_items c on c.id=l.content_item_id
    join public.brand_sites b on b.id=c.brand_site_id
   order by coalesce(l.scheduled_for,now()+interval '365 days'),l.priority desc,l.created_at;
end;
$$;

revoke all on function public.claim_publishing_jobs(text,integer,integer) from public, anon, authenticated;
grant execute on function public.claim_publishing_jobs(text,integer,integer) to service_role;

create or replace function public.ack_publishing_job(
  p_job_id uuid,
  p_status text,
  p_external_post_id text default null,
  p_external_permalink text default null,
  p_scheduled_at timestamptz default null,
  p_published_at timestamptz default null,
  p_error text default null,
  p_executor_metadata jsonb default '{}'::jsonb
) returns public.publishing_outbox
language plpgsql
security definer
set search_path = public
as $$
declare v_row public.publishing_outbox%rowtype;
begin
  if p_status not in ('approved','leased','scheduled','published','failed','cancelled') then
    raise exception 'invalid publishing status';
  end if;

  update public.publishing_outbox
     set status=p_status,
         external_post_id=coalesce(p_external_post_id,external_post_id),
         external_permalink=coalesce(p_external_permalink,external_permalink),
         scheduled_for=coalesce(p_scheduled_at,scheduled_for),
         published_at=case when p_status='published' then coalesce(p_published_at,now()) else published_at end,
         last_error=p_error,
         executor_metadata=executor_metadata || coalesce(p_executor_metadata,'{}'::jsonb),
         lease_expires_at=case when p_status='leased' then lease_expires_at else null end,
         updated_at=now()
   where id=p_job_id
   returning * into v_row;
  if not found then raise exception 'publishing job not found'; end if;

  if p_status='published' and not exists(
    select 1 from public.publishing_outbox o where o.content_item_id=v_row.content_item_id and o.status not in ('published','cancelled')
  ) then
    update public.content_items set status='completed',updated_at=now() where id=v_row.content_item_id;
  end if;
  return v_row;
end;
$$;

revoke all on function public.ack_publishing_job(uuid,text,text,text,timestamptz,timestamptz,text,jsonb) from public, anon, authenticated;
grant execute on function public.ack_publishing_job(uuid,text,text,text,timestamptz,timestamptz,text,jsonb) to service_role;

create or replace function public.list_publishing_reconcile_jobs(p_limit integer default 200)
returns table(id uuid, external_post_id text, status text, platform text)
language sql
security definer
set search_path = public
as $$
  select o.id,o.external_post_id,o.status,o.platform
  from public.publishing_outbox o
  where o.external_post_id is not null and o.status in ('scheduled','leased')
  order by o.updated_at desc
  limit greatest(1,least(coalesce(p_limit,200),500));
$$;

revoke all on function public.list_publishing_reconcile_jobs(integer) from public, anon, authenticated;
grant execute on function public.list_publishing_reconcile_jobs(integer) to service_role;
