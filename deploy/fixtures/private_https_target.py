"""Fictional HTTPS endpoint for disposable, internally networked integration tests."""
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import ssl

STATE=Path("/fixture/state")
class Target(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!="/ready":
            self.send_response(404)
        else:
            state=STATE.read_text().strip() if STATE.exists() else "healthy"
            self.send_response(503 if state=="failed" else 200)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(b'{"service":"fictional","ready":true}')
    def log_message(self,*args): pass

server=HTTPServer(("0.0.0.0",443),Target)
tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain("/fixture/tls.crt","/fixture/tls.key")
server.socket=tls.wrap_socket(server.socket,server_side=True)
server.serve_forever()
