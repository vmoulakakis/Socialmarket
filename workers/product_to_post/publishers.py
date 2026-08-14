from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import quote

import requests

ALIASES={
    'facebook':['facebook'],
    'instagram':['instagram','instagram-standalone'],
    'tiktok':['tiktok'],
    'linkedin':['linkedin','linkedin-page'],
}

def public_media_url(supabase_url:str,storage_path:str)->str:
    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/creatives/{quote(storage_path,safe='/')}"

class PostizPublisher:
    def __init__(self)->None:
        self.base=os.getenv('POSTIZ_API_URL','https://api.postiz.com/public/v1').rstrip('/')
        self.key=os.getenv('POSTIZ_API_KEY','').strip()
        self.session=requests.Session()
        if self.key:self.session.headers.update({'Authorization':self.key})
    @property
    def configured(self)->bool:return bool(self.key)
    def _json(self,method:str,path:str,body:dict[str,Any]|None=None,timeout:int=60):
        if not self.configured:raise RuntimeError('postiz_not_configured')
        r=self.session.request(method,f'{self.base}{path}',json=body,headers={'Content-Type':'application/json'} if body is not None else None,timeout=timeout)
        try:payload=r.json() if r.text else {}
        except Exception:payload={'raw':r.text[:1200]}
        if not r.ok:raise RuntimeError(f'postiz_http_{r.status_code}:{json.dumps(payload,ensure_ascii=False)[:1000]}')
        return payload
    def integrations(self):
        payload=self._json('GET','/integrations')
        return payload if isinstance(payload,list) else payload.get('integrations',[])
    def integration_for(self,platform:str):
        override=os.getenv(f'POSTIZ_INTEGRATION_{platform.upper()}','').strip()
        integrations=[x for x in self.integrations() if not x.get('disabled')]
        if override:
            hit=next((x for x in integrations if x.get('id')==override),None)
            if hit:return hit
        aliases=set(ALIASES.get(platform,[platform]))
        hit=next((x for x in integrations if str(x.get('identifier') or '').lower() in aliases),None)
        if not hit:raise RuntimeError(f'postiz_integration_missing:{platform}')
        return hit
    def upload_from_url(self,url:str):
        return self._json('POST','/upload-from-url',{'url':url},90)
    def schedule(self,platform:str,scheduled_at:str,text:str,media_url:str):
        integration=self.integration_for(platform)
        uploaded=self.upload_from_url(media_url)
        settings={'__type':str(integration.get('identifier') or platform)}
        if platform=='instagram':settings['post_type']='post'
        payload={'type':'schedule','date':scheduled_at,'shortLink':False,'tags':[],'posts':[{
            'integration':{'id':integration['id']},
            'value':[{'content':text,'image':[{'id':uploaded['id'],'path':uploaded['path']}]}],
            'settings':settings,
        }]}
        result=self._json('POST','/posts',payload,90)
        first=result[0] if isinstance(result,list) and result else result
        return {'provider':'postiz','external_post_id':(first or {}).get('postId'),'response':result,'payload':payload}
    def health(self,platform:str):
        if not self.configured:return {'configured':False,'healthy':False,'reason':'POSTIZ_API_KEY_missing'}
        try:return {'configured':True,'healthy':True,'integration':self.integration_for(platform)}
        except Exception as exc:return {'configured':True,'healthy':False,'reason':str(exc)[:500]}

class BufferPublisher:
    def __init__(self)->None:
        self.supabase_url=os.environ['SUPABASE_URL'].rstrip('/')
        self.key=os.environ['SUPABASE_SERVICE_ROLE_KEY']
        self.session=requests.Session();self.session.headers.update({'Authorization':f'Bearer {self.key}','apikey':self.key,'Content-Type':'application/json'})
    @property
    def configured(self)->bool:return True
    def request(self,action:str,body:dict[str,Any]|None=None,timeout:int=90):
        r=self.session.request('POST' if body is not None else 'GET',f'{self.supabase_url}/functions/v1/buffer-sync/{action}',json=body,timeout=timeout)
        try:payload=r.json()
        except Exception:payload={'raw':r.text[:1000]}
        if not r.ok or payload.get('error'):raise RuntimeError(f"buffer_sync:{r.status_code}:{json.dumps(payload,ensure_ascii=False)[:900]}")
        return payload
    def schedule(self,platform:str,scheduled_at:str,text:str,media_url:str):
        result=self.request('schedule',{'platform':platform,'scheduledAt':scheduled_at,'text':text,'mediaUrl':media_url})
        return {'provider':'buffer','external_post_id':result.get('postId'),'response':result,'payload':{'platform':platform,'scheduledAt':scheduled_at,'mediaUrl':media_url}}
    def health(self,platform:str):
        try:
            data=self.request('channels',{})
            matches=[x for x in data.get('channels',[]) if str(x.get('service') or '').lower()==platform]
            healthy=any(not x.get('isDisconnected') and not x.get('isLocked') for x in matches)
            return {'configured':True,'healthy':healthy,'channels':matches}
        except Exception as exc:return {'configured':False,'healthy':False,'reason':str(exc)[:500]}

class PublisherRouter:
    def __init__(self)->None:
        self.postiz=PostizPublisher();self.buffer=BufferPublisher();self.mode=os.getenv('PUBLISHER_MODE','hybrid').strip().lower()
    def order(self,platform:str,preferred:str='auto'):
        if preferred=='postiz':return [self.postiz,self.buffer]
        if preferred=='buffer':return [self.buffer,self.postiz]
        if self.mode=='postiz':return [self.postiz]
        if self.mode=='buffer':return [self.buffer]
        return [self.buffer,self.postiz] if platform=='tiktok' else [self.postiz,self.buffer]
    def schedule(self,platform:str,scheduled_at:str,text:str,storage_path:str,preferred:str='auto'):
        media_url=public_media_url(os.environ['SUPABASE_URL'],storage_path);errors=[]
        for provider in self.order(platform,preferred):
            name=provider.__class__.__name__.replace('Publisher','').lower()
            try:
                if not provider.configured:errors.append(f'{name}:not_configured');continue
                result=provider.schedule(platform,scheduled_at,text,media_url);result['media_url']=media_url;result['fallback_errors']=errors;return result
            except Exception as exc:errors.append(f'{name}:{str(exc)[:700]}')
        raise RuntimeError('publisher_router_failed|'+'|'.join(errors))
