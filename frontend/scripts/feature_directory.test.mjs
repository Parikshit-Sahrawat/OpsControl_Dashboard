import test from 'node:test';
import assert from 'node:assert/strict';
import {FEATURE_GROUPS,visibleFeatureGroups} from '../src/featureDirectory.js';
test('directory uses unique existing destinations and excludes retired capabilities',()=>{
 const items=FEATURE_GROUPS.flatMap(g=>g.items);assert.equal(new Set(items.map(([p,,s])=>p+':'+(s||''))).size,items.length);
 assert.equal(items.some(i=>/incident|kubernetes|servicenow|sftp/i.test(i.join(' '))),false);
});
test('directory permission filtering fails closed and reacts to revocation',()=>{
 assert.deepEqual(visibleFeatureGroups({permissions:[]}),[]);
 const visible=visibleFeatureGroups({permissions:['resources.view']});
 assert.deepEqual(visible.find(g=>g.name==='Resource Management').items.map(i=>i[2]),['compute-instances','data-pipelines','apis']);
 assert.equal(visible.some(g=>g.name==='Access Management'),false);
 assert.deepEqual(visibleFeatureGroups({permissions:[],authorization_revision:2}),[]);
});

test('approved Resource Management hierarchy has distinct existing inventories and monitoring labels',()=>{
 assert.deepEqual(FEATURE_GROUPS.find(g=>g.name==='Resource Management').items.map(i=>i[1]),['Organizations','Compute Instances','Data Pipelines','APIs','Collectors','Monitoring Templates','Event Parameters','Alert Rules','Notification Delivery']);
 assert.deepEqual(FEATURE_GROUPS.find(g=>g.name==='Operations').items.map(i=>i[1]),['Data Pipeline Monitoring','Compute Health','API Endpoint Monitoring','Alerts','Reports']);
 assert.equal(FEATURE_GROUPS.flatMap(g=>g.items).some(i=>i[1]==='Data Sources / Resources'),false);
});
