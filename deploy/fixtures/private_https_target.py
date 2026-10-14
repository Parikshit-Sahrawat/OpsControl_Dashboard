"""Fictional HTTPS application and read-only Carte-shaped endpoint for CI."""
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import ssl
STATE=Path("/fixture/state")
class Target(BaseHTTPRequestHandler):
    def do_GET(self):
        state=STATE.read_text().strip() if STATE.exists() else "healthy"
        route=urlsplit(self.path)
        if route.path=="/ready":
            status=503 if state=="failed" else 200
            body=b'{"service":"fictional","ready":true}'
            kind="application/json"
        elif route.path in ("/kettle/jobStatus/","/kettle/jobStatus"):
            query=parse_qs(route.query,strict_parsing=False)
            if set(query)!={"name","id","xml"} or query.get("xml")!=["Y"]:
                status,body,kind=400,b"Invalid read-only Carte query","text/plain"
            else:
                status=200
                job_status="Running" if state=="running" else "Finished"
                errors=2 if state=="failed" else 0
                execution_id=query["id"][0]
                if not execution_id.isascii() or len(execution_id)>100:
                    status,body,kind=400,b"Invalid id","text/plain"
                else:
                    body=(
                        "<job_status><id>"+execution_id+"</id>"+
                        "<status_desc>"+job_status+"</status_desc>"+
                        "<result><nr_errors>"+str(errors)+"</nr_errors></result>"+
                        "</job_status>").encode()
                    kind="application/xml"
        else:
            status,body,kind=404,b"Not found","text/plain"
        self.send_response(status)
        self.send_header("Content-Type",kind)
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*args): pass
server=HTTPServer(("0.0.0.0",443),Target)
tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain("/fixture/tls.crt","/fixture/tls.key")
server.socket=tls.wrap_socket(server.socket,server_side=True)
server.serve_forever()
