"""ETL parsing, bounded source evidence, schedule/timezone and runtime semantics."""
import os, socket
from datetime import datetime, timezone
from types import SimpleNamespace
from app.worker.pentaho_status import parse_carte_status, get_job_status, PentahoStatusError, safe_text
from app.services.etl_monitoring import expected_window, runtime_status
from app.schemas.etl import JobOrderCreate
from pydantic import ValidationError

def denied(call):
    try:call()
    except (ValueError,ValidationError):return
    raise AssertionError('Invalid ETL input accepted')

def main():
    now=datetime(2026,10,11,10,0,tzinfo=timezone.utc)
    assert runtime_status('RUNNING',now, None,60,120,now)[0]=='RUNNING'
    from datetime import timedelta
    assert runtime_status('RUNNING',now-timedelta(seconds=60),None,60,120,now)==('LONG_RUNNING','ON_TRACK')
    assert runtime_status('RUNNING',now-timedelta(seconds=120),None,60,120,now)==('LONG_RUNNING','BREACHED')
    assert runtime_status('RUNNING',None,None,60,120,now)==('RUNNING','UNKNOWN')
    job=SimpleNamespace(schedule={'timezone':'Asia/Kolkata'},expected_window_start='14:00',expected_window_end='15:00',no_run_grace_seconds=900)
    assert expected_window(job,now)==(datetime(2026,10,11,8,30,tzinfo=timezone.utc),datetime(2026,10,11,9,45,tzinfo=timezone.utc))
    job.expected_window_start='23:00';job.expected_window_end='01:00'
    assert expected_window(job,datetime(2026,10,11,0,0,tzinfo=timezone.utc))[0]==datetime(2026,10,10,17,30,tzinfo=timezone.utc)
    job.schedule['weekdays']=[0];assert expected_window(job,now) is None
    xml=b'<job-status><id>one</id><status_desc>Finished</status_desc><nr_errors>1</nr_errors><jobentry_results><jobentry_result><name>Load warehouse</name><result><nr_errors>1</nr_errors></result><comment>password="two words"</comment></jobentry_result></jobentry_results><log_text>token=hidden</log_text></job-status>'
    result=parse_carte_status(xml,True)
    assert result['execution_status']=='FAILED' and result['steps'][0]['status']=='FAILED'
    assert 'two words' not in result['steps'][0]['error_message'] and 'hidden' not in result['logs']
    assert result['started_at'] is None
    for body in (b'<!DOCTYPE foo><job-status/>',b'x'*65537,b'<unexpected/>',b'<job-status><id>x</id><status>Finished</status><nr_errors>-1</nr_errors></job-status>'):denied(lambda:parse_carte_status(body))
    assert 'secret-value' not in safe_text('https://reader:secret-value@private.example.test')
    os.environ['OPSCONTROL_LOCAL_ALLOWED_HOSTS']='carte.example.test'
    os.environ['OPSCONTROL_LOCAL_ALLOWED_CIDRS']='10.42.0.0/24'
    cfg={'url':'https://carte.example.test','job_name':'Warehouse','allowed_hosts':['carte.example.test'],'allowed_cidrs':['10.42.0.0/24'],'credential_ref':'fixture'}
    resolver=lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.42.0.4',443))]
    calls=[]
    def transport(host,ip,path,basic):
        assert host=='carte.example.test' and ip=='10.42.0.4' and basic
        calls.append(path)
        if path.startswith('/kettle/status/'):
            return 200,b'<server_status><job_status_list><job_status><jobname>Warehouse</jobname><id>one</id></job_status><job_status><jobname>Other job</jobname><id>unapproved</id></job_status></job_status_list></server_status>'
        assert 'unapproved' not in path
        return 200,xml
    snapshot=get_job_status(cfg,transport,resolver,lambda ref:('reader','private-value'))
    assert snapshot['inventory_complete'] and len(snapshot['executions'])==1 and len(calls)==2
    denied(lambda:get_job_status(cfg,lambda *a:(503,b'<error/>'),resolver,lambda ref:('reader','private-value')))
    denied(lambda:get_job_status({**cfg,'url':'http://carte.example.test'},transport,resolver))
    for patch in ({'timezone':'No/Such/Zone'},{'sla_seconds':1},{'expected_window_start':'25:00','expected_window_end':'26:00'}):
        denied(lambda:JobOrderCreate(organization_id='00000000-0000-0000-0000-000000000001',hostname='test',name='test',**({'expected_runtime_seconds':60,'sla_seconds':120}|patch)))
    print('ETL PARSING / SCHEDULE / SLA / CREDENTIAL REDACTION / READ-ONLY BOUNDARIES PASS')

if __name__=='__main__':main()
