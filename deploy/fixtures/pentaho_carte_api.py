"""Controlled read-only Carte-shaped HTTPS API; never a genuine Pentaho server."""
import base64, json, os, ssl, sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from xml.sax.saxutils import escape

private=Path(sys.argv[1]); host=sys.argv[2]
expected='Basic '+base64.b64encode(('fixture-reader:'+ (private/'carte-password').read_text().strip()).encode()).decode()
job='Fictional Daily Warehouse'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def response(self,status,body):
        journal_name='http-requests.jsonl' if urlsplit(self.path).path=='/ready' else 'carte-requests.jsonl'
        with (private/journal_name).open('a') as journal:
            journal.write(json.dumps({'method':self.command,'path':urlsplit(self.path).path,'status':status})+'\n')
        self.send_response(status);self.send_header('Content-Type','application/xml');self.end_headers();self.wfile.write(body.encode())
    def do_GET(self):
        # Optional Sprint 4 public readiness endpoint shares the controlled TLS
        # server; Carte paths retain their separate read-only authentication.
        if self.path == '/ready' and (private/'http-status').is_file():
            return self.response(int((private/'http-status').read_text()), '<health>Controlled HTTPS service</health>')
        if self.headers.get('Authorization')!=expected:return self.response(401,'<error>Authentication required</error>')
        phase=(private/'phase').read_text().strip()
        if phase=='poll-failed':return self.response(503,'<error>Controlled unavailability</error>')
        parts=urlsplit(self.path);query=parse_qs(parts.query)
        if parts.path=='/kettle/status/' and query=={'xml':['Y']}:
            entry='' if phase=='no-run' else '<job_status><jobname>'+job+'</jobname><id>controlled-'+phase+'</id></job_status>'
            return self.response(200,'<server_status><job_status_list>'+entry+'</job_status_list></server_status>')
        if parts.path!='/kettle/jobStatus/' or query!={'name':[job],'id':['controlled-'+phase],'xml':['Y']}:
            return self.response(403,'<error>Read-only fixed paths only</error>')
        now=datetime.now(timezone.utc); elapsed={'running':5,'long-running':90,'sla-breach':150,'failed':45,'recovered':30}[phase]
        status='Finished' if phase in {'failed','recovered'} else 'Running'
        errors=2 if phase=='failed' else 0
        started=(now-timedelta(seconds=elapsed)).isoformat()
        ended='<end_date>'+(now-timedelta(seconds=1)).isoformat()+'</end_date>' if status=='Finished' else ''
        message='Warehouse connection refused' if errors else 'Read-only fixture execution status'
        logs=message+' password="'+(private/'carte-password').read_text().strip()+'" token=fixture-sensitive-marker'
        entries='<jobentry_results><jobentry_result><name>Extract customers</name><result><nr_errors>0</nr_errors></result></jobentry_result><jobentry_result><name>Load warehouse</name><result><nr_errors>'+str(errors)+'</nr_errors></result><comment>'+message+'</comment></jobentry_result></jobentry_results>'
        # This controlled SUCCESS phase includes native result evidence. A
        # finished status and zero errors alone cannot establish success.
        native_result='<result><result>Y</result><nr_errors>0</nr_errors></result>' if phase=='recovered' else ''
        return self.response(200,'<job-status><id>controlled-'+phase+'</id><status_desc>'+status+'</status_desc><nr_errors>'+str(errors)+'</nr_errors>'+native_result+'<start_date>'+started+'</start_date>'+ended+entries+'<log_text>'+escape(logs)+'</log_text></job-status>')
    def do_POST(self):self.response(403,'<error>Mutation forbidden</error>')
    do_DELETE=do_POST
    do_PUT=do_POST

server=ThreadingHTTPServer((os.getenv('ETL_FIXTURE_BIND',host),443),Handler)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(private/'tls.crt',private/'tls.key')
server.socket=context.wrap_socket(server.socket,server_side=True)
server.serve_forever()
