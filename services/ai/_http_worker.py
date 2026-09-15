"""Private one-shot transport child. Secrets travel over stdin, never argv/logs.

The parent terminates this process at a wall-clock deadline (including DNS).
No eval imports, shell, redirects, implicit proxy, SDK retry or tools/files API.
"""
from __future__ import annotations
import json, sys, os, math, threading
import requests

ENDPOINT='https://ai.api.cloud.yandex.net/v1/chat/completions'
MAX_RESPONSE=262144

def perform(payload:dict) -> dict:
    try:
        headers=payload['headers'];body=payload['body'];timeout=payload['timeout']
        if not isinstance(headers,dict) or headers.get('x-data-logging-enabled')!='false':
            return {'ok':False,'code':'configuration','retryable':False,'unknown':False}
        with requests.Session() as session:
            session.trust_env=False
            # A single connection, no retry adapter installed. Responses are bounded.
            with session.post(ENDPOINT,headers=headers,json=body,timeout=(min(5,timeout),timeout),
                              stream=True,allow_redirects=False) as r:
                code=r.status_code
                if code!=200:
                    retry=code in {429,502,503,504}
                    error='rate_limited' if code==429 else ('upstream_error' if code in {502,503,504} else ('permission_denied' if code in {401,403} else 'invalid_request'))
                    # Do not read an error body; it may contain credentials or input.
                    return {'ok':False,'code':error,'retryable':retry,'unknown':code not in {400,401,403,404,429}}
                chunks=[];size=0
                for chunk in r.iter_content(chunk_size=8192):
                    size+=len(chunk)
                    if size>MAX_RESPONSE:return {'ok':False,'code':'invalid_envelope','retryable':False,'unknown':True}
                    chunks.append(chunk)
                envelope=json.loads(b''.join(chunks))
                if not isinstance(envelope,dict):raise ValueError
                return {'ok':True,'envelope':envelope}
    except requests.exceptions.ConnectTimeout:
        return {'ok':False,'code':'transport_unknown','retryable':False,'unknown':True}
    except requests.exceptions.Timeout:
        return {'ok':False,'code':'timeout_unknown','retryable':False,'unknown':True}
    except Exception:
        return {'ok':False,'code':'transport_unknown','retryable':False,'unknown':True}

def main():
    try:
        raw=sys.stdin.buffer.read(131073)
        if len(raw)>131072:raise ValueError
        payload=json.loads(raw)
        timeout=payload.get('timeout')
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0 < timeout <= 25:
            raise ValueError
        # An orphan child is bounded even if the parent process is terminated.
        watchdog=threading.Timer(timeout+2,lambda:os._exit(124))
        watchdog.daemon=True
        watchdog.start()
        result=perform(payload)
        watchdog.cancel()
    except Exception:
        result={'ok':False,'code':'configuration','retryable':False,'unknown':False}
    sys.stdout.write(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
