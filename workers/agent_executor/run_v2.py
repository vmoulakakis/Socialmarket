import json
import run as base


def preview_task(task):
    prior=(task.get('payload') or {}).get('prior') or {}
    sha=base.recursive_find(prior,'commitSha')
    if not sha:
        raise base.TaskError('preview requires prior commitSha')

    deployments=json.loads(base.sh([
        'gh','api',f'repos/{base.REPO}/deployments?sha={sha}&per_page=20'
    ],timeout=60).stdout or '[]')
    if not deployments:
        raise base.TaskError('Vercel deployment not available yet',retry=True)

    # Vercel/GitHub may expose more than one deployment for the same SHA.
    # Prefer a transient/preview deployment, but accept any matching SHA.
    ordered=sorted(
        deployments,
        key=lambda d:(not bool(d.get('transient_environment')),d.get('created_at') or ''),
        reverse=True,
    )
    pending=False
    for deployment in ordered:
        deployment_id=deployment.get('id')
        if not deployment_id:
            continue
        statuses=json.loads(base.sh([
            'gh','api',f'repos/{base.REPO}/deployments/{deployment_id}/statuses?per_page=20'
        ],timeout=60).stdout or '[]')
        for status in statuses:
            state=str(status.get('state') or '').lower()
            if state in ('pending','queued','in_progress'):
                pending=True
                continue
            if state!='success':
                continue
            environment_url=status.get('environment_url')
            if not environment_url or not str(environment_url).startswith('http'):
                continue
            return {
                'previewUrl':environment_url,
                'commitSha':sha,
                'provider':'vercel',
                'deploymentId':deployment_id,
                'environment':status.get('environment') or deployment.get('environment'),
                'status':'success',
                'logUrl':status.get('log_url') or status.get('target_url'),
            }

    if pending:
        raise base.TaskError('Vercel preview still pending',retry=True)
    raise base.TaskError('No successful Vercel deployment environment URL found')


base.preview_task=preview_task

if __name__=='__main__':
    base.main()
