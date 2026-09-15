import os, json, time, hashlib, requests
from collections import Counter

FEED_URL=os.environ['LINKWISE_FEED_URL']
REPORT_PATH=os.getenv('LINKWISE_PROFILE_REPORT','linkwise_feed_profile.json')
CHUNK_BYTES=int(os.getenv('LINKWISE_PROFILE_CHUNK_BYTES', str(1024*1024)))


def stream_profile():
    started=time.time()
    sha=hashlib.sha256()
    bytes_seen=0
    chunks=0
    content_length=None
    content_type=None
    status=None

    # IMPORTANT: profiler is intentionally read-only. It never writes products to VMDB.
    with requests.get(FEED_URL, stream=True, timeout=(30, 300), allow_redirects=True) as r:
        status=r.status_code
        r.raise_for_status()
        content_type=r.headers.get('content-type')
        try: content_length=int(r.headers.get('content-length',''))
        except ValueError: content_length=None
        for block in r.iter_content(chunk_size=CHUNK_BYTES):
            if not block: continue
            sha.update(block)
            bytes_seen += len(block)
            chunks += 1

    elapsed=max(time.time()-started,0.001)
    report={
        'mode':'read_only_stream_profile',
        'http_status':status,
        'content_type':content_type,
        'content_length_header':content_length,
        'bytes_seen':bytes_seen,
        'size_mb':round(bytes_seen/1024/1024,2),
        'size_gb':round(bytes_seen/1024/1024/1024,4),
        'chunks':chunks,
        'sha256':sha.hexdigest(),
        'elapsed_seconds':round(elapsed,2),
        'throughput_mb_s':round(bytes_seen/1024/1024/elapsed,2),
        'note':'No database writes performed. Record-level JSON profiling is the next stage after transport sizing.'
    }
    with open(REPORT_PATH,'w',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    stream_profile()
