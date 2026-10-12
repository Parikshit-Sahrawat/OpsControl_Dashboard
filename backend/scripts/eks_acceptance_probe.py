"""Real API/DB tenant and dry-run/import acceptance with guarded AWS SDK stubs."""
import json
import os
from pathlib import Path
from sqlalchemy import select,func
from app.db.session import SessionLocal
from app.models import Organization,DataSource,Collector
from scripts import remote_protocol_probe as p
from scripts.eks_acceptance_fixture import ACCOUNT,REGION

def main():
    if os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE')!='1' or os.getenv('ENVIRONMENT')!='demo':
        raise SystemExit('Explicit disposable EKS release lab required')
    p.BASE=os.environ['TEST_API_BASE']
    def login(name):return p.check(200,'POST','/api/v1/auth/login',body={'username':name,'password':p.PASSWORD})['access_token']
    admin,north,south=login('test-admin'),login('test-north'),login('test-south')
    with SessionLocal() as db: org_id=str(db.scalar(select(Organization.id).where(Organization.code=='LAB-N')))
    source=p.check(201,'POST','/api/v1/resource-management/data-sources',admin,
        {'organization_id':org_id,'name':'AWS EKS discovery fixture','source_type':'AWS_EKS',
         'connection_config':{'region':REGION,'account_id':ACCOUNT}})
    path='/api/v1/resource-discovery/sources/'+source['id']
    caps=p.check(200,'GET','/api/v1/resource-discovery/capabilities',admin)
    assert next(c for c in caps if c['provider']=='AWS_EKS')['monitoring'] is False
    p.check(403,'POST',path+'/scan',north,{})
    p.check(404,'POST',path+'/scan',south,{})
    scan=p.check(200,'POST',path+'/scan',admin,{})
    assert len(scan['candidates'])==2 and all(c['monitoring_status']=='NOT_CONFIGURED' for c in scan['candidates'])
    serialized=json.dumps(scan)
    assert 'untrusted-control-plane' not in serialized and 'synthetic-cert' not in serialized
    chosen=scan['candidates'][0]['external_id']
    def count():
        with SessionLocal() as db:return db.scalar(select(func.count()).select_from(DataSource))
    before=count()
    dry=p.check(200,'POST',path+'/import',admin,{'approved_external_ids':[chosen],'dry_run':True})
    assert dry['resources'][0]['action']=='WOULD_IMPORT' and count()==before
    imported=p.check(200,'POST',path+'/import',admin,{'approved_external_ids':[chosen],'dry_run':False})
    resource=imported['resources'][0]
    assert resource['action']=='IMPORTED' and count()==before+1
    repeated=p.check(200,'POST',path+'/import',admin,{'approved_external_ids':[chosen],'dry_run':False})
    assert repeated['resources'][0]['action']=='ALREADY_IMPORTED' and repeated['resources'][0]['data_source_id']==resource['data_source_id']
    assert count()==before+1
    p.check(422,'POST',path+'/import',admin,{'approved_external_ids':['unapproved-cluster'],'dry_run':False})
    p.check(422,'POST','/api/v1/data-sources/'+resource['data_source_id']+'/activations',admin,
        {'rule_version_ids':[],'include_templates':False})
    collectors=p.check(200,'GET','/api/v1/resource-management/collectors?data_source_id='+resource['data_source_id'],admin)
    assert collectors==[]
    from uuid import UUID
    with SessionLocal() as db:
        row=db.get(DataSource,UUID(resource['data_source_id']))
        assert row.status=='UNKNOWN' and row.organization_id==UUID(org_id) and row.source_type=='AWS_EKS'
        assert row.connection_config=={'region':REGION,'account_id':ACCOUNT,'cluster_names':['sequence-eks']}
    bad=p.check(201,'POST','/api/v1/resource-management/data-sources',admin,
        {'organization_id':org_id,'name':'Denied EKS endpoint fixture','source_type':'AWS_EKS',
         'connection_config':{'region':REGION,'account_id':ACCOUNT,'endpoint_url':'http://169.254.169.254'}})
    p.check(422,'POST','/api/v1/resource-discovery/sources/'+bad['id']+'/scan',admin,{})
    out=Path(os.getenv('RELEASE_EVIDENCE_DIR','/tmp/opscontrol-release-evidence'));out.mkdir(parents=True,exist_ok=True)
    report={'status':'PASS','origin':'Real HTTP API and PostgreSQL; actual boto3/botocore Stubber controlled responses, no AWS request',
        'checks':['STS expected account checked before read-only EKS list/describe','Cluster endpoint/certificate omitted',
                  'Tenant administrator/foreign tenant discovery denied','Dry run writes no inventory',
                  'Approved import is idempotent and remains UNKNOWN with no collector','Unapproved endpoint/reference rejected'],
        'candidates':2,'imported_clusters':1,'limitations':['Genuine EKS workload IAM/API acceptance deferred; live AWS remains paused',
                                                    'Inventory is not Pod/Deployment/Node health; use approved in-cluster collector']}
    (out/'eks.json').write_text(json.dumps(report,indent=2)+'\n')
    print('READ-ONLY EKS SDK / API / DRY-RUN / IMPORT / TENANT ACCEPTANCE PASS')

if __name__=='__main__':main()
