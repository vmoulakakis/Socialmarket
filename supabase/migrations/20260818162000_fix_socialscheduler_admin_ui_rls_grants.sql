-- SocialScheduler Admin UI hotfix: authenticated admin access without public exposure.

grant select, insert, update on table public.socialscheduler_creative_assets to authenticated;
grant select on table public.socialscheduler_recovery_events to authenticated;

drop policy if exists socialscheduler_admin_recovery_select on public.socialscheduler_recovery_events;
create policy socialscheduler_admin_recovery_select
on public.socialscheduler_recovery_events
for select
to authenticated
using (
  lower(coalesce(auth.jwt() ->> 'email', '')) = 'vmoulakakis@gmail.com'
);
