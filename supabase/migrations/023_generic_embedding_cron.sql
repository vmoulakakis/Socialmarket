select cron.unschedule(jobid) from cron.job where jobname='socialmarket-generic-embedding-worker';
select cron.schedule(
  'socialmarket-generic-embedding-worker',
  '*/5 * * * *',
  $$select net.http_post(
      url := (select decrypted_secret from vault.decrypted_secrets where name='merchant_worker_project_url') || '/functions/v1/generic-embedding-worker',
      headers := jsonb_build_object(
        'Content-Type','application/json',
        'Authorization','Bearer ' || (select decrypted_secret from vault.decrypted_secrets where name='merchant_worker_auth_token'),
        'apikey',(select decrypted_secret from vault.decrypted_secrets where name='merchant_worker_auth_token')
      ),
      body := jsonb_build_object('limit',10,'source','pg_cron'),
      timeout_milliseconds := 120000
    );$$
);
