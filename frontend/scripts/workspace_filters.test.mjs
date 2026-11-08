import test from "node:test";
import assert from "node:assert/strict";
import { readResourceFilters, writeResourceFilters, validateResourceFilters, configurationCapable } from "../src/workspaceFilters.js";
test("resource URL round trip includes only known non-secret filter keys", () => {
 const query=writeResourceFilters("keep=1",{customer:"a",environment:"DEV",search:"alpha & beta",active:"false",domain:"API",token:"forbidden"});
 assert(!query.includes("token"));assert.equal(new URLSearchParams(query).get("keep"),"1");
 assert.deepEqual(readResourceFilters(query),{customer:"a",environment:"DEV",search:"alpha & beta",active:"false",domain:"API"});
});
test("forged bookmark never silently broadens customer scope",()=>{
 assert.match(validateResourceFilters({customer:"foreign",domain:"VM"},[{id:"a"}]),/unavailable/);
 assert.equal(validateResourceFilters({customer:"a",domain:"VM",active:"false"},[{id:"a"}]),"");
 assert.match(validateResourceFilters({environment:"arbitrary"},[]),/supported environment/);
 assert.match(validateResourceFilters({active:"healthy"},[]),/configuration state/);
});
test("configuration affordance derives from selected customer permissions",()=>{
 const user={permissions:["resources.update"],customer_permissions:{a:["resources.view"],b:["resources.update"]}};
 assert.equal(configurationCapable(user,["a"]),false);assert.equal(configurationCapable(user,["b"]),true);
 assert.equal(configurationCapable({platform_admin:true},[]),true);
});
