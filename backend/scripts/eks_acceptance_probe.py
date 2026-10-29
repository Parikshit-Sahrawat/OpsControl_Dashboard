"""Real API/DB tenant and dry-run/import acceptance with guarded AWS SDK stubs."""
import json
import os
from pathlib import Path
from sqlalchemy import select,func
from app.db.session import SessionLocal
from app.models import Organization,DataSource,Collector
from scripts import remote_protocol_probe as p
ACCOUNT,REGION="123456789012","ap-south-1"

def main():
    if os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE')!='1' or os.getenv('ENVIRONMENT')!='demo':
        raise SystemExit('Explicit disposable EKS release lab required')
    p.BASE=os.environ['TEST_API_BASE']
    def login(name):return p.check(200,'POST','/api/v1/auth/login',body={'username':name,'password':p.PASSWORD})['access_token']
    admin,north,south=login('test-admin'),login('test-north'),login('test-south')
    with SessionLocal() as db: org_id=str(db.scalar(select(Organization.id).where(Organization.code=='LAB-N')))
    payload={'organization_id':org_id,'name':'AWS EKS legacy fixture','source_type':'AWS_EKS',
             'connection_config':{'region':REGION,'account_id':ACCOUNT}}
    p.check(422,'POST','/api/v1/resource-management/data-sources',admin,payload)
    # Only direct synthetic fixture insertion may create retired historical rows.
    with SessionLocal() as db:
        legacy=DataSource(**payload)
        db.add(legacy);db.commit();source={'id':str(legacy.id)}
    path='/api/v1/resource-discovery/sources/'+source['id']
    caps=p.check(200,'GET','/api/v1/resource-discovery/capabilities',admin)
    assert all(c['provider']!='AWS_EKS' for c in caps)
    p.check(403,'POST',path+'/scan',north,{})
    p.check(404,'POST',path+'/scan',south,{})
    # Kubernetes/EKS discovery is retired: preserve authorization and verify
    # the API refuses both scanning and importing without creating inventory.
    def count():
        with SessionLocal() as db:return db.scalar(select(func.count()).select_from(DataSource))
    before=count()
    p.check(422,'POST',path+'/scan',admin,{})
    p.check(422,'POST',path+'/import',admin,{'approved_external_ids':['aws:123456789012:ap-south-1:eks:sequence-eks'],'dry_run':True})
    p.check(422,'POST',path+'/import',admin,{'approved_external_ids':['aws:123456789012:ap-south-1:eks:sequence-eks'],'dry_run':False})
    assert count()==before
    p.check(422,'POST','/api/v1/data-sources/'+source['id']+'/activations',admin,
        {'rule_version_ids':[],'include_templates':False})
    collectors=p.check(200,'GET','/api/v1/resource-management/collectors?data_source_id='+source['id'],admin)
    assert collectors==[]
    out=Path(os.getenv('RELEASE_EVIDENCE_DIR','/tmp/opscontrol-release-evidence'));out.mkdir(parents=True,exist_ok=True)
    report={'status':'PASS','origin':'Real HTTP API and PostgreSQL; no AWS request',
        'checks':['EKS discovery and import rejected for platform administrator',
                  'Tenant authorization and foreign tenant denial retained',
                  'Rejected operations do not create inventory or collectors',
                  'New EKS monitoring activation rejected'],
        'candidates':0,'imported_clusters':0,
        'limitations':['Historical association compatibility verified separately by database acceptance tests']}
    (out/'eks.json').write_text(json.dumps(report,indent=2)+'\\n')
    print('EKS RETIREMENT / API / TENANT ACCEPTANCE PASS')

if __name__=='__main__':main()
