"""Loopback-only design specimen; fonts stay in an external, verified cache."""
import argparse, hashlib, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--port-file',type=Path,required=True);args=parser.parse_args()
args.cache.mkdir(parents=True,exist_ok=True)
for item in json.loads((root/'FONT_PROVENANCE.json').read_text())['records']:
    f=args.cache/item['filename']
    if not f.exists():f.write_bytes(urlopen(item['url'],timeout=45).read())
    if hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Font checksum mismatch')
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        path=self.path.split('?')[0]
        if path in ('/','/specimen.html'):file=root/'specimen.html';kind='text/html'
        elif path.startswith('/fonts/') and Path(path).name in {x['filename'] for x in json.loads((root/'FONT_PROVENANCE.json').read_text())['records']}:
            file=args.cache/Path(path).name;kind='font/ttf'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',kind);self.end_headers();self.wfile.write(file.read_bytes())
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
args.port_file.write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','pid':__import__('os').getpid()}))
server.serve_forever()
