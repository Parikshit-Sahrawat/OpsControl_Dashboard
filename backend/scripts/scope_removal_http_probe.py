"""Owned synthetic real-HTTP removal contracts; no provider network requests."""
import hashlib
import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select,func,text
from app.db.session import SessionLocal
from app.models import Organization,DataSource,Collector,CollectorRun
from scripts import remote_protocol_probe as p


def main():
    if os.getenv('OPSCONTROL_RELEASE_ACCEPTANCE')!='1' or os.getenv('ENVIRONMENT')!='demo':
        raise SystemExit('Owned disposable release fixture required')
    p.BASE=os.environ['TEST_API_BASE']
    checks=[]
    def check(status,method,path,token=None,body=None):
        result=p.check(status,method,path,token,body)
        checks.append({'method':method,'path':path,'expected':status,'actual':status})
        return result
    admin=check(200,'POST','/api/v1/auth/login',body={'username':'test-admin','password':p.PASSWORD})['access_token']
    north=check(200,'POST','/api/v1/auth/login',body={'username':'test-north','password':p.PASSWORD})['access_token']
    south=check(200,'POST','/api/v1/auth/login',body={'username':'test-south','password':p.PASSWORD})['access_token']
    reader=check(200,'POST','/api/v1/auth/login',body={'username':'test-reader','password':p.PASSWORD})['access_token']
    with SessionLocal() as db:
        org=db.scalar(select(Organization).where(Organization.code=='LAB-N'))
        org_id=str(org.id)
        legacy=DataSource(organization_id=org.id,name='scope-legacy-do-not-operate',source_type='AWS_EKS')
        db.add(legacy);db.flush();legacy_id=str(legacy.id);db.commit()
    from tests.test_kubernetes_cluster_associations import KubernetesClusterAssociationTests
    fixture=KubernetesClusterAssociationTests();fixture.setUp();fixture.db.commit();fixture.doCleanups()
    def legacy_hashes():
        with SessionLocal() as db:
            return {table:hashlib.sha256("\n".join(db.execute(text(f'SELECT row_to_json(t)::text FROM {table} t ORDER BY id')).scalars()).encode()).hexdigest()
                    for table in ('kubernetes_clusters','kubernetes_cluster_associations','kubernetes_cluster_association_decisions')}
    before=legacy_hashes()
    root='/api/v1/resource-management'
    aliases=('KUBERNETES','K8S','AWS_EKS','AZURE_AKS','GOOGLE_GKE','OPENSHIFT','AmazonElasticKubernetesService','microk8s','k3s','awsEks','azureAks','gcpGke')
    for kind in aliases:
        payload={'organization_id':org_id,'name':'excluded-'+kind,'source_type':kind}
        check(422,'POST',root+'/data-sources',admin,payload)
        check(422,'POST','/api/v1/monitoring/data-sources',admin,payload)
    sources=[]
    for kind in ('LINUX_HOST','WINDOWS_HOST','AWS_EC2','HTTP','PENTAHO'):
        sources.append(check(201,'POST',root+'/data-sources',north,{'organization_id':org_id,'name':'scope-supported-'+kind,'source_type':kind}))
    source_id=sources[-2]['id']
    for config in ({'nested':[{'provider':'AKS'}]}, {'opscontrol':{'monitoring_overrides':{'collector':{'type':'K8S'}}}}, {'receivers':{'k8s_cluster':{}}}):
        check(422,'PATCH',root+'/data-sources/'+source_id,north,{'connection_config':config})
        check(422,'POST',root+'/collectors',north,{'name':'nested','data_source_id':source_id,'collector_type':'HTTP','configuration':config})
        check(422,'POST','/api/v1/monitoring/templates',admin,{'name':'nested','package_config':config})
    for prefix in (root,'/api/v1/monitoring'):
        check(422,'PATCH',prefix+'/data-sources/'+legacy_id,admin,{'enabled':True})
        check(422,'PATCH',prefix+'/data-sources/'+legacy_id,admin,{'source_type':'HTTP'})
        check(422,'POST',prefix+'/collectors',admin,{'data_source_id':legacy_id,'name':'legacy-http','collector_type':'HTTP'})
    check(404,'GET','/api/v1/monitoring/data-sources/'+legacy_id,south)
    check(403,'POST',root+'/collectors',reader,{'data_source_id':source_id,'name':'denied','collector_type':'HTTP'})
    for suffix,payload in (('scan',{}),('import',{'approved_external_ids':['synthetic'],'dry_run':False})):
        check(422,'POST','/api/v1/resource-discovery/sources/'+legacy_id+'/'+suffix,admin,payload)
    check(422,'POST','/api/v1/data-sources/'+legacy_id+'/activations',admin,{'rule_version_ids':[],'include_templates':False})
    template=check(201,'POST','/api/v1/monitoring/templates',admin,{'name':'scope-supported-template','package_config':{'collector':{'type':'HTTP'}}})
    check(422,'POST','/api/v1/monitoring/data-sources/'+legacy_id+'/templates',admin,{'template_id':template['id']})
    check(201,'POST','/api/v1/monitoring/data-sources/'+source_id+'/templates',admin,{'template_id':template['id']})
    check(422,'POST','/api/v1/monitoring/data-sources/'+source_id+'/templates',admin,{'template_id':template['id'],'overrides':{'collector':{'type':'OpenShift'}}})
    for domain in ('VM','ETL','API'):
        check(422,'POST','/api/v1/unified/import/validate',north,{'domain':domain,'format':'JSON','content':json.dumps({'collector':{'type':'Kubernetes'}})})
    for suffix in ('','/'+str(uuid4()),'/'+str(uuid4())+'/associations/'+org_id):
        status,_=p.req('GET',root+'/kubernetes-clusters'+suffix,admin)
        assert status in (403,404,405),status
        checks.append({'method':'GET','path':root+'/kubernetes-clusters'+suffix,'actual':status,'expected':'403/404/405'})
    # Prove direct persisted legacy collector cannot execute through the local loop.
    with SessionLocal() as db:
        c=Collector(data_source_id=legacy_id,name='scope-legacy-persisted-http',collector_type='HTTP',configuration={'url':'https://forbidden.example.test'},enabled=True)
        db.add(c);db.commit();cid=c.id
        from app.worker.collector_runtime import _execute_locked
        asyncio.run(_execute_locked(cid,db))
        db.refresh(c);assert c.enabled is False
        assert db.scalar(select(func.count()).select_from(CollectorRun).where(CollectorRun.collector_id==cid))==0
    after=legacy_hashes()
    assert before==after, 'Retired interfaces mutated legacy history'
    result={'status':'PASS','http_checks':checks,'http_count':len(checks),'local_execution':'retired before provider call; zero runs',
            'legacy_hashes_before':before,'legacy_hashes_after':after,'legacy_source_id':legacy_id,'supported_source_ids':[s['id'] for s in sources],
            'limitations':['Synthetic endpoints only; not genuine provider certification']}
    out=Path(os.environ['RELEASE_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
    (out/'scope-http.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SCOPE REMOVAL HTTP PASS',len(checks))

if __name__=='__main__':main()
