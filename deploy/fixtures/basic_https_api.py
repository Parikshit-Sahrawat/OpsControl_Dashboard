"""Fictional Basic-auth service for an isolated TLS/Docker acceptance lab."""
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import ssl

ROOT = Path('/fixture')
credentials = json.loads((ROOT/'credentials.json').read_text())
authorization = 'Basic ' + base64.b64encode((credentials['username']+':'+credentials['password']).encode()).decode()
class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        authenticated = self.headers.get('Authorization') == authorization
        status = 401 if not authenticated else 302 if self.path == '/redirect' else 503 if (ROOT/'state').read_text().strip() == 'failed' else 200
        # Persist only sanitized fixture facts, never headers or credentials.
        with (ROOT/'reads.jsonl').open('a') as out:
            out.write(json.dumps({'status':status, 'authenticated':authenticated, 'path':self.path})+'\n')
        self.send_response(status)
        if status == 302: self.send_header('Location', 'https://unapproved.example.test/')
        body = b'{"synthetic":true}'
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *_): pass
server = HTTPServer(('0.0.0.0',443), Fixture)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(ROOT/'tls.crt',ROOT/'tls.key')
server.socket = context.wrap_socket(server.socket,server_side=True)
server.serve_forever()
