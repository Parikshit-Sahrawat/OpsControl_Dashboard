"""Synthetic TLS GET/HEAD target; no outbound traffic, credentials or control APIs."""

import ssl
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Target(BaseHTTPRequestHandler):
    def respond(self, head=False):
        state = Path("/fixture/state").read_text().strip()
        if self.path == "/slow":
            time.sleep(0.1)
        status = 503 if state == "failed" else 200
        body = b'{"synthetic":true}'
        if self.path.startswith("/kettle/jobStatus/"):
            status = 200
            body = b"<job_status><id>dev05-1</id><status_desc>Finished</status_desc><result><result>Y</result><nr_errors>0</nr_errors><exit_status>0</exit_status></result></job_status>"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_GET(self):
        self.respond()

    def do_HEAD(self):
        self.respond(True)

    def log_message(self, *args):
        pass


server = HTTPServer(("0.0.0.0", 443), Target)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("/fixture/tls.crt", "/fixture/tls.key")
server.socket = context.wrap_socket(server.socket, server_side=True)
server.serve_forever()
