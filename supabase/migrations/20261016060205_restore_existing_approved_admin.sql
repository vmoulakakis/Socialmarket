-- Restore the existing verified account already pinned by AuthGate and the app configuration.
-- Never provision users or infer an administrator from a submitted email address.
insert into public.admin_emails(email)
select 'vmoulakakis@gmail.com'
where exists(select 1 from auth.users where lower(email)='vmoulakakis@gmail.com' and email_confirmed_at is not null)
on conflict(email) do nothing;
