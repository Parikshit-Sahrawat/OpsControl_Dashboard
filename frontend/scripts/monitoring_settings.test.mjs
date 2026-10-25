import test from 'node:test';
import assert from 'node:assert/strict';
import {createHydrationGuard, defaultMonitoringSettings, readMonitoringSettings, hydrateMonitoringSettings} from '../src/monitoringSettings.js';
const saved = {data_source_id:'source-a',enabled:true,remote_worker_id:'worker-a',configuration:{
  url:'https://fixture.example.test/ready',method:'HEAD',expected_status:204,timeout_seconds:5,
  max_response_time_ms:10000,headers:{'x-opscontrol-check':'dev05-ui',Authorization:'must-not-copy'},credential_ref:'must-not-copy'}};
const activation = {status:'ACTIVE',collector_id:'collector-a',rule_version_ids:['metric-v1','alert-v1'],include_templates:true};
const request = async path => path.endsWith('/activation') ? activation : saved;
test('authorized active collector restores all editable settings and pinned selections without copying credentials',async()=>{
  assert.deepEqual(await readMonitoringSettings(request,'source-a'),{
    url:'https://fixture.example.test/ready',method:'HEAD',status:'204',timeout:'5',latency:'10000',header:'dev05-ui',
    workerId:'worker-a',rules:['metric-v1','alert-v1'],includeTemplates:true});
});
test('legacy default GET settings remain explicit and optional assertions empty',async()=>{
  const result=await readMonitoringSettings(async path=>path.endsWith('/activation')?activation:{...saved,configuration:{}},'source-a');
  assert.deepEqual({...result,workerId:'',rules:[],includeTemplates:false},defaultMonitoringSettings());
});
for(const status of ['NOT_CONFIGURED','DISABLED']) test(status+' does not fetch or restore a historical collector',async()=>{
  let calls=0;
  const result=await readMonitoringSettings(async()=>{calls++;return {...activation,status};},'source-a');
  assert.deepEqual(result,defaultMonitoringSettings());assert.equal(calls,1);
});
test('disabled collector resets controls; a collector belonging to another source fails closed',async()=>{
  assert.deepEqual(await readMonitoringSettings(async path=>path.endsWith('/activation')?activation:{...saved,enabled:false},'source-a'),defaultMonitoringSettings());
  await assert.rejects(readMonitoringSettings(request,'source-b'),/does not belong/);
});
test('out-of-order source fetch cannot replace the selected source or organization',async()=>{
  const guard=createHydrationGuard();let release;
  const a=guard.begin();const pending=new Promise(resolve=>{release=resolve;});
  let shown='b';const old=pending.then(()=>{if(guard.current(a))shown='a';});
  const b=guard.begin();release();await old;assert.equal(shown,'b');assert.equal(guard.current(b),true);
  guard.invalidate();assert.equal(guard.current(b),false);
});
test('pending hydration preserves actual user edits and invalidates an in-flight preview',async()=>{
  const guard=createHydrationGuard();let resolve, shown, ready=false;
  const pending=new Promise(r=>{resolve=r;});
  hydrateMonitoringSettings(async path=>path.endsWith('/activation')?pending:saved,'source-a',guard,
    value=>{shown=value;},()=>{ready=true;},error=>{throw error;});
  const preview=guard.ticket();
  shown={...shown,method:'GET',latency:'250',header:'unsaved'};guard.edit();
  resolve(activation);await new Promise(resolve=>setImmediate(resolve));
  assert.equal(ready,true);assert.equal(shown.header,'unsaved');assert.equal(shown.latency,'250');
  assert.equal(guard.current(preview),false);assert.equal(guard.sameSource(preview),true);
});
test('source switch cancels a real pending settings read and no stale state or error is applied',async()=>{
  const guard=createHydrationGuard();let resolve, shown;
  const pending=new Promise(r=>{resolve=r;});const errors=[];
  const cancel=hydrateMonitoringSettings(async path=>path.endsWith('/activation')?pending:saved,'source-a',guard,
    value=>{shown=value;},()=>{},error=>errors.push(error));
  cancel();
  hydrateMonitoringSettings(async()=>({status:'NOT_CONFIGURED'}),'source-b',guard,
    value=>{shown=value;},()=>{},error=>errors.push(error));
  resolve(activation);await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(shown,defaultMonitoringSettings());assert.deepEqual(errors,[]);
});
test('permission failures propagate instead of silently exposing an editable default configuration',async()=>{
  await assert.rejects(readMonitoringSettings(async()=>{throw Error('Not authorized');},'source-a'),/Not authorized/);
});
test('saved selections are applied before controls become ready',async()=>{
  const guard=createHydrationGuard();let shown, ready=false;
  hydrateMonitoringSettings(request,'source-a',guard,value=>{shown=value;},()=>{
    assert.deepEqual(shown.rules,['metric-v1','alert-v1']);assert.equal(shown.method,'HEAD');ready=true;
  },error=>{throw error;});
  assert.equal(ready,false);
  await new Promise(resolve=>setImmediate(resolve));assert.equal(ready,true);
});
