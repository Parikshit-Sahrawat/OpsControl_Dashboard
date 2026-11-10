import test from "node:test";
import assert from "node:assert/strict";
import { canOpenSection, readSectionRoute, sectionHash } from "../src/navigation.js";

const user = (permissions) => ({ permissions });

test("approved child hashes open only existing authorized sections", () => {
  const resource = user(["customers.view", "resources.view", "collectors.view"]);
  assert.deepEqual(readSectionRoute("#/resources/organizations", resource), ["Resource Management", "organizations"]);
  assert.deepEqual(readSectionRoute("#/resources/collectors", resource), ["Resource Management", "collectors"]);
  assert.equal(readSectionRoute("#/resources/collectors", user(["customers.view", "resources.view"])), null);
  assert.equal(readSectionRoute("#/resources/organizations", user(["resources.view"])), null);
  assert.equal(readSectionRoute("#/resources/unknown", resource), null);
});

test("organizational access is an access view, never a customer grant", () => {
  const viewer = user(["access.view"]);
  assert.equal(canOpenSection(viewer, "Access Management", "Organisational Access"), true);
  assert.equal(canOpenSection(viewer, "Access Management", "Access Audit"), false);
  assert.equal(readSectionRoute("#/access/organisational-access", user([])), null);
  assert.equal(sectionHash("Access Management", "Organisational Access"), "#/access/organisational-access");
  assert.equal(sectionHash("Resource Management", "collectors"), "#/resources/collectors");
});

test("configuration sections have stable guarded routes", () => {
  const viewer = user(["resources.view", "templates.view"]);
  for (const [section, path] of [
    ["parameters", "#/resources/event-parameters"],
    ["rules", "#/resources/alert-rules"],
    ["delivery", "#/resources/notification-delivery"],
  ]) {
    assert.equal(sectionHash("Resource Management", section), path);
    assert.deepEqual(readSectionRoute(path, viewer), ["Resource Management", section]);
    assert.equal(readSectionRoute(path, user(["resources.view"])), null);
    assert.deepEqual(readSectionRoute(path, user(["templates.view"])), section === "delivery" ? ["Resource Management", section] : null);
  }
});

test('domain management routes are explicit, revocable and independent of monitoring permissions',async()=>{
 const {resourceDomainForSection,resourceSectionForDomain,readPageRoute,pageHash}=await import('../src/navigation.js');
 for(const [section,domain] of [['compute-instances','VM'],['data-pipelines','ETL'],['apis','API']]){
  const path='#/resources/'+section;
  assert.equal(resourceDomainForSection(section),domain);assert.equal(resourceSectionForDomain(domain),section);
  assert.equal(sectionHash('Resource Management',section),path);
  assert.deepEqual(readSectionRoute(path,user(['resources.view'])),['Resource Management',section]);
  assert.equal(readSectionRoute(path,user(['etl.view'])),null);assert.equal(readSectionRoute(path,user([])),null);
 }
 assert.equal(resourceDomainForSection('__proto__'),undefined);assert.equal(canOpenSection(user(['resources.view']),'Resource Management','toString'),false);
 assert.deepEqual(readSectionRoute('#/resources/data-resources',user(['resources.view'])),['Resource Management','resources']);
 for(const page of ['Overview','Compute Health','API Endpoint Monitoring','Alerts','Reports']){
  const {NAV_PERMISSIONS}=await import('../src/permissions.js');
  assert.equal(readPageRoute(pageHash(page),user([NAV_PERMISSIONS[page]])),page);assert.equal(readPageRoute(pageHash(page),user([])),null);
 }
});
