from __future__ import annotations

from datetime import datetime,timedelta,timezone
from .common import SupabaseREST,first_row

def ensure_month_plan(db:SupabaseREST):
    settings=(first_row(db.get('app_settings','key=eq.autonomous_social_engine&select=value&limit=1')) or {}).get('value') or {}
    if settings.get('enabled') is False:return {'created':False,'reason':'engine_disabled'}
    horizon=int(settings.get('horizon_days') or 30);requested=int(settings.get('requested_products') or 10);platforms=settings.get('platforms') or ['facebook','instagram','tiktok','linkedin']
    now=datetime.now(timezone.utc);coverage=now+timedelta(days=max(10,horizon//2))
    existing=db.get('social_content_calendar',f"scheduled_at=gte.{now.isoformat()}&scheduled_at=lte.{coverage.isoformat()}&status=in.(approved,scheduled,published)&select=id&limit=1") or []
    active=db.get('product_to_post_runs','status=in.(queued,processing)&mode=eq.auto&select=id,status&limit=1') or []
    if existing or active:return {'created':False,'reason':'coverage_or_run_exists'}
    row=first_row(db.post('product_to_post_runs',{'mode':'auto','requested_count':max(1,min(requested,30)),'platforms':platforms,'horizon_days':max(7,min(horizon,90)),'strategy':'maximum_expected_conversion','audience_context':{'autonomous':True,'selection':'price>=100, high demand, positive forecast, low competition, strong offer, trusted merchant'},'status':'queued','priority':50}))
    return {'created':bool(row),'run_id':(row or {}).get('id'),'reason':'new_month_plan'}

if __name__=='__main__':print(ensure_month_plan(SupabaseREST()))
