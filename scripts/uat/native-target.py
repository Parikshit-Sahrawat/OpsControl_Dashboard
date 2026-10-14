"""Owned TLS fixture only; health and metadata are explicitly controlled inputs."""

import json, ssl, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        state = json.loads(Path("/fixture/target.json").read_text())
        if self.path == "/records":
            if (
                self.headers.get("INFA-SESSION-ID")
                != Path("/fixture/provider-token").read_text()
            ):
                self.send_response(401)
                self.end_headers()
                return
            code, body = 200, {"records": state.get("records", [])}
        else:
            code, body = state["http_status"], {"origin": "CONTROLLED_OWNED_TLS_TARGET"}
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


for _ in range(300):
    if Path("/fixture/ca.pem").exists() and Path("/fixture/key.pem").exists():
        break
    time.sleep(0.1)
server = HTTPServer(("0.0.0.0", 8443), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("/fixture/ca.pem", "/fixture/key.pem")
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
