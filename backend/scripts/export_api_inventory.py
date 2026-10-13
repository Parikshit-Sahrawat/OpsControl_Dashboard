"""Offline complete HTTP route inventory, including FastAPI lazy included routers.

No DB connection or authentication value is inspected. This is a coverage input,
not proof of authorization. Production routes depend on the selected environment.
"""
import argparse
import json
from pathlib import Path
from app.main import app
from app.security.http import _ALLOWED_PUBLIC, _WORKER_PUBLIC_GATE, _AGENT_GATE

def inventory():
    rows=[]
    for included in app.routes:
        contexts = getattr(included,'effective_route_contexts',None)
        routes = contexts() if callable(contexts) else [included]
        for route in routes:
            path=getattr(route,'path',None)
            if not path: continue
            methods=sorted(getattr(route,'methods',None) or ['WEBSOCKET'])
            identity=('agent-enrollment-or-bearer' if path in _AGENT_GATE or path.startswith('/api/v1/agent/') else
                      'worker-bearer' if path in _WORKER_PUBLIC_GATE else
                      'public/ingress-policy' if path in _ALLOWED_PUBLIC else 'human-bearer/route-policy')
            endpoint=getattr(route,'endpoint',None)
            rows.append({'path':path,'methods':methods,'name':getattr(route,'name',None),
                'tags':getattr(route,'tags',[]),'include_in_schema':getattr(route,'include_in_schema',True),
                'endpoint':getattr(endpoint,'__module__','')+'.'+getattr(endpoint,'__qualname__',''),
                'identity_hint':identity,'authorization_review':'REQUIRED'})
    return sorted(rows,key=lambda row:(row['path'],row['methods']))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    args=parser.parse_args(); rows=inventory()
    # A partial root-only inventory is not a passing review prerequisite.
    if not any(row['path']=='/api/v1/worker/heartbeat' for row in rows):
        raise RuntimeError('Included worker routes missing from inventory')
    operations={(row['path'],method) for row in rows for method in row['methods']}
    documented={(path,method.upper()) for path,item in app.openapi()['paths'].items()
                for method in item if method.upper() in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS','TRACE'}}
    if not documented <= operations:
        raise RuntimeError('Documented API operations missing from route inventory')
    args.output.write_text(json.dumps(rows,indent=2)+'\n')
    print('Inventoried HTTP routes:',len(rows))

if __name__=='__main__':main()
