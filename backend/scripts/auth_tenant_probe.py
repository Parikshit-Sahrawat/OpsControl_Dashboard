"""Fail-closed identity and tenant checks against disposable local staging.

Requires migrated database + running API at localhost:8000.
Fixture data is wholly fictional; exits nonzero on any security breach.
"""
import json
import os
import urllib.error
import urllib.request
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Organization, DataSource, Collector, VM, JobOrder, JobOrderHistory, ExecutionType, ExecutionStatus
from app.security.models import User, OrganizationMembership
from app.security.passwords import hash_password

BASE = os.getenv("TEST_API_BASE", "http://127.0.0.1:8000")
PASSWORD = "testing-only-StrongPassword-123!"

def seed():
    with SessionLocal() as db:
        a, b = Organization(name="Example North Lab", code="LAB-N"), Organization(name="Example South Lab", code="LAB-S")
        db.add_all([a, b]); db.flush()
        sa, sb = DataSource(organization_id=a.id,name="north-synthetic",source_type="API"), DataSource(organization_id=b.id,name="south-synthetic",source_type="API")
        db.add_all([sa,sb]); db.flush()
        ca, cb = Collector(data_source_id=sa.id,name="north-probe",collector_type="API"), Collector(data_source_id=sb.id,name="south-probe",collector_type="API")
        db.add_all([ca,cb])
        va, vb = VM(organization_id=a.id, hostname="lab-n-vm"), VM(organization_id=b.id, hostname="lab-s-vm")
        db.add_all([va,vb]); db.flush()
        ja, jb = JobOrder(organization_id=a.id,vm_id=va.id,name="lab-n-job"), JobOrder(organization_id=b.id,vm_id=vb.id,name="lab-s-job")
        db.add_all([ja,jb]);db.flush()
        ha,hb = JobOrderHistory(job_order_id=ja.id,execution_type=ExecutionType.SCHEDULED,status=ExecutionStatus.SUCCESS,started_at=datetime.now(timezone.utc)),JobOrderHistory(job_order_id=jb.id,execution_type=ExecutionType.SCHEDULED,status=ExecutionStatus.FAILED,started_at=datetime.now(timezone.utc))
        db.add_all([ha,hb]); db.flush()
        admin=User(username="test-admin", password_hash=hash_password(PASSWORD), platform_admin=True)
        user=User(username="test-north", password_hash=hash_password(PASSWORD))
        other=User(username="test-south", password_hash=hash_password(PASSWORD))
        reader=User(username="test-reader", password_hash=hash_password(PASSWORD))
        mixed=User(username="test-mixed", password_hash=hash_password(PASSWORD))
        db.add_all([admin,user,other,reader,mixed]); db.flush()
        db.add_all([
            OrganizationMembership(user_id=user.id,organization_id=a.id,role="org_admin"),
            OrganizationMembership(user_id=other.id,organization_id=b.id,role="org_admin"),
            OrganizationMembership(user_id=reader.id,organization_id=a.id,role="viewer"),
            OrganizationMembership(user_id=mixed.id,organization_id=a.id,role="org_admin"),
            OrganizationMembership(user_id=mixed.id,organization_id=b.id,role="viewer"),
        ])
        result={"a":str(a.id),"b":str(b.id),"sa":str(sa.id),"sb":str(sb.id),"ca":str(ca.id),"cb":str(cb.id),"ha":str(ha.id),"hb":str(hb.id)}
        db.commit();return result

def call(method,path,token=None,body=None):
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,headers=headers,data=data,method=method)
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            return r.status, json.loads(r.read() or b"null") if r.status!=204 else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")

def login(name):
    status,result=call("POST","/api/v1/auth/login",body={"username":name,"password":PASSWORD})
    assert status==200,(name,status,result)
    return result["access_token"]

def expect(status,method,path,token=None,body=None):
    got,response=call(method,path,token,body)
    assert got==status,{"method":method,"path":path,"expected":status,"got":got,"response":response}
    print("PASS",status,method,path)
    return response

def main():
    ids=seed()
    org="/api/v1/organizations"
    source="/api/v1/resource-management/data-sources"
    legacy="/api/v1/monitoring/data-sources"
    expect(401,"GET",org)
    expect(401,"GET",source)
    expect(401,"GET",legacy+"/"+ids["sb"])
    expect(401,"PATCH",source+"/"+ids["sa"],body={"name":"bad"})
    expect(401,"GET","/api/v1/etl/executions")
    expect(401,"GET","/api/v1/monitoring/templates")
    a=login("test-north");b=login("test-south");reader=login("test-reader");mixed=login("test-mixed");admin=login("test-admin")
    identity=expect(200,"GET","/api/v1/auth/me",a)
    assert identity["username"]=="test-north" and len(identity["memberships"])==1,identity
    result=expect(200,"GET",org,a)
    assert {x["id"] for x in result}=={ids["a"]},result
    result=expect(200,"GET",source,a)
    assert {x["id"] for x in result}=={ids["sa"]},result
    result=expect(200,"GET",legacy,a)
    assert {x["id"] for x in result}=={ids["sa"]},result
    result=expect(200,"GET",source+"?organization_id="+ids["b"],a)
    assert result==[],result
    expect(404,"GET",legacy+"/"+ids["sb"],a)
    expect(404,"PATCH",source+"/"+ids["sb"],a,{"name":"illegal"})
    expect(404,"PATCH",legacy+"/"+ids["sb"],a,{"name":"illegal"})
    expect(404,"GET","/api/v1/monitoring/collectors/"+ids["cb"],a)
    expect(404,"GET","/api/v1/monitoring/collectors/"+ids["cb"]+"/runs",a)
    etl=expect(200,"GET","/api/v1/etl/executions",a)
    assert {x["id"] for x in etl}=={ids["ha"]},etl
    expect(404,"GET","/api/v1/etl/executions/"+ids["hb"],a)
    expect(404,"GET","/api/v1/etl/executions/"+ids["hb"]+"/investigation",a)
    expect(404,"POST","/api/v1/etl/executions/"+ids["hb"]+"/correlation",a)
    etl=expect(200,"GET","/api/v1/etl/executions",b)
    assert {x["id"] for x in etl}=={ids["hb"]},etl
    expect(404,"POST",source,a,{"organization_id":ids["b"],"name":"forged","source_type":"API"})
    expect(403,"POST",org,a,{"name":"Forged","code":"FORGED"})
    expect(403,"POST",source,reader,{"organization_id":ids["a"],"name":"illegal","source_type":"API"})
    result=expect(200,"GET",org,mixed); assert {x["id"] for x in result}=={ids["a"],ids["b"]}
    expect(403,"PATCH",source+"/"+ids["sb"],mixed,{"name":"cross-tenant-mutation"})
    expect(403,"POST",source,mixed,{"organization_id":ids["b"],"name":"mixed-forge","source_type":"API"})
    result=expect(200,"GET",org,b); assert {x["id"] for x in result}=={ids["b"]}
    result=expect(200,"GET",org,admin); assert {x["id"] for x in result}=={ids["a"],ids["b"]}
    expect(201,"POST",source,a,{"organization_id":ids["a"],"name":"authorized-probe","source_type":"API"})
    expect(204,"POST","/api/v1/auth/logout",a)
    expect(401,"GET",org,a)
    print("ALL TENANT NEGATIVE TESTS PASS")

if __name__=="__main__": main()
