create or replace function public.socialmarket_is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $function$
  select lower(coalesce(auth.jwt()->>'email','')) = 'vmoulakakis@gmail.com';
$function$;
