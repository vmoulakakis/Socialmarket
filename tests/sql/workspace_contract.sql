-- Run as the database owner in a disposable transaction; no application data is changed.
begin;
select set_config('request.jwt.claims',jsonb_build_object('sub',(select id from auth.users where email='vmoulakakis@gmail.com'),'email','vmoulakakis@gmail.com','role','authenticated')::text,true);
set local role authenticated;
do $$
declare a jsonb; b jsonb; s text;
begin
 foreach s in array array['overview','products','curation','creatives','outbox','analytics','configuration','optimization','merchants','problems'] loop
  a:=public.socialmarket_workspace(s);
  if a->>'source'<>'canonical_vmdb' or jsonb_typeof(a->'rows')<>'array' then raise exception 'invalid_contract_%',s; end if;
 end loop;
 a:=public.socialmarket_workspace('products','',10,0);
 b:=public.socialmarket_workspace('products','',10,10);
 if jsonb_array_length(a->'rows')<>10 then raise exception 'pagination_size'; end if;
 if exists(select 1 from jsonb_array_elements(a->'rows') x join jsonb_array_elements(b->'rows') y on x->>'id'=y->>'id') then raise exception 'pagination_overlap'; end if;
 a:=public.socialmarket_workspace('products','not-a-real-product-9a811e',10,0);
 if (a->>'total')::int<>0 or jsonb_array_length(a->'rows')<>0 then raise exception 'search_contract'; end if;
 begin
  perform public.socialmarket_workspace('unknown');raise exception 'section_allowlist_failed';
 exception when invalid_parameter_value then null;
 end;
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-0000-0000-000000000001","email":"other@example.invalid","role":"authenticated"}',true);
do $$ begin perform public.socialmarket_workspace();raise exception 'non_admin_allowed';exception when insufficient_privilege then null;end $$;
reset role;
set local role anon;
do $$ begin perform public.socialmarket_workspace();raise exception 'anon_allowed';exception when insufficient_privilege then null;end $$;
rollback;
