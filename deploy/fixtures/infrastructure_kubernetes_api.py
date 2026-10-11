"""Controlled Kubernetes HTTPS API fixture, not a genuine cluster.

Actual SDK requests require the fixture reader token and verified TLS. Its
fixed namespace/node read policy rejects secrets, other namespaces and writes.
"""
import hmac
import json
import ssl
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
root=Path(sys.argv[1])

def pod(name,failed):
    return {'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':'infra-lab','uid':'pod-fixture-1'},
        'spec':{'containers':[{'name':'web','image':'fictional:controlled'}]},
        'status':{'phase':'Running','conditions':[{'type':'Ready','status':'False' if failed else 'True'}],
            'containerStatuses':[{'name':'web','image':'fictional:controlled','imageID':'fixture',
                'ready':not failed,'restartCount':2 if failed else 0,'state':{'running':{}}}]}}

def deployment(failed):
    return {'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'web','namespace':'infra-lab','uid':'deployment-fixture-1'},
        'spec':{'replicas':2,'selector':{'matchLabels':{'app':'web'}},'template':{'metadata':{'labels':{'app':'web'}},'spec':{'containers':[{'name':'web','image':'fictional:controlled'}]}}},
        'status':{'readyReplicas':0 if failed else 2,'availableReplicas':0 if failed else 2}}

def node(failed):
    return {'apiVersion':'v1','kind':'Node','metadata':{'name':'fixture-node','uid':'node-fixture-1'},
        'spec':{'unschedulable':False},'status':{'conditions':[{'type':'Ready','status':'True'},
            {'type':'MemoryPressure','status':'True' if failed else 'False'},
            {'type':'DiskPressure','status':'False'},{'type':'PIDPressure','status':'False'}]}}

class Handler(BaseHTTPRequestHandler):
    def respond(self,status,body):
        raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        token=(root/'kube-token').read_text().strip()
        if not hmac.compare_digest(self.headers.get('Authorization',''),'Bearer '+token): return self.respond(401,{'kind':'Status','message':'Unauthorized','code':401})
        failed=(root/'phase').read_text().strip()=='failed'
        path=self.path.split('?')[0]
        routes={'/api/v1/namespaces/infra-lab/pods/web-0':pod('web-0',failed),
            '/api/v1/namespaces/infra-lab/pods':{'kind':'PodList','apiVersion':'v1','metadata':{},'items':[pod('web-0',failed)]},
            '/apis/apps/v1/namespaces/infra-lab/deployments/web':deployment(failed),
            '/apis/apps/v1/namespaces/infra-lab/deployments':{'kind':'DeploymentList','apiVersion':'apps/v1','metadata':{},'items':[deployment(failed)]},
            '/api/v1/nodes/fixture-node':node(failed)}
        if path not in routes:return self.respond(403,{'kind':'Status','message':'Read policy denied','code':403})
        self.respond(200,routes[path])
    def do_POST(self):self.respond(403,{'kind':'Status','message':'Read only','code':403})
    do_DELETE=do_POST
    do_PATCH=do_POST
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',18443),Handler)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(root/'tls.crt',root/'tls.key')
server.socket=context.wrap_socket(server.socket,server_side=True);server.serve_forever()
