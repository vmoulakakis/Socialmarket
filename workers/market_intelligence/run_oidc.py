import run as core
from gateway import db_call

def api(method,path,params=None,data=None,prefer=None):
    return db_call(method,path,params=params,data=data,prefer=prefer)

def rpc(name,payload):
    return db_call('POST',f'rpc/{name}',data=payload)

core.api=api
core.rpc=rpc

if __name__=='__main__':
    core.main()
