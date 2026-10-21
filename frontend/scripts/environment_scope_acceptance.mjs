import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

// Read-only HTTP checks against a separately created, disposable UAT state.
const state = process.env.OPSCONTROL_UAT_STATE_DIR;
if (!state) throw new Error("OPSCONTROL_UAT_STATE_DIR is required");
const settings = JSON.parse(fs.readFileSync(path.join(state, "settings.json"), "utf8"));
if (!settings.project?.startsWith("opscontrol-s14-uat-")) throw new Error("UAT-owned project required");
const users = JSON.parse(fs.readFileSync(path.join(state, "uat-users.json"), "utf8"));
users["demo-admin"] = fs.readFileSync(path.join(state, "admin-password"), "utf8").trim();
const base = `http://127.0.0.1:${settings.api_port}`;
let checks = 0;
function check(value, label) { assert.ok(value, label); checks++; console.log(`PASS ${label}`); }
async function login(username) {
  const response = await fetch(base + "/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: users[username] }),
  });
  assert.equal(response.status, 200, `login ${username}`);
  return (await response.json()).access_token;
}
async function request(token, customerIds, pathname) {
  const response = await fetch(base + pathname, { headers: {
    Authorization: `Bearer ${token}`,
    "X-OpsControl-Customers": customerIds.join(","),
  } });
  return { status: response.status, body: await response.json() };
}
const admin = await login("demo-admin");
const scope = await request(admin, [], "/api/v1/auth/customer-scope");
assert.equal(scope.status, 200);
const a = scope.body.find((row) => row.code === "UAT-A")?.id;
const b = scope.body.find((row) => row.code === "UAT-B")?.id;
check(Boolean(a && b), "two synthetic customer IDs discovered");
const ids = [a, b];
const endpoints = [
  ["/api/v1/unified/resources?domain=VM", (body) => body.total],
  ["/api/v1/unified/overview?", (body) => Object.values(body.domains).reduce((sum, domain) => sum + domain.resources, 0)],
  ["/api/v1/unified/domain-state/VM?", (body) => body.total],
  ["/api/v1/unified/alerts?", (body) => body.total],
  ["/api/v1/unified/correlations?", (body) => body.total],
  ["/api/v1/unified/reports/VM?", (body) => body.resources.length],
  ["/api/v1/native-incidents?", (body) => body.total],
  ["/api/v1/etl/executions?", (body) => body.length],
];
for (const [path, count] of endpoints) {
  const separator = path.includes("?") && !path.endsWith("?") ? "&" : "";
  const q = (params) => path + separator + params;
  const single = await request(admin, ids, q("environment=SANDBOX"));
  const multiple = await request(admin, ids, q("environments=SANDBOX&environments=DEV"));
  const other = await request(admin, ids, q("environments=DEV"));
  const conflict = await request(admin, ids, q("environment=SANDBOX&environments=DEV"));
  check(single.status === 200 && multiple.status === 200 && other.status === 200, `${path} accepts scalar and explicit multi-environment filters`);
  check(count(single.body) === count(multiple.body) && count(other.body) <= count(single.body), `${path} retains SANDBOX evidence without inventing DEV records`);
  check(conflict.status === 422, `${path} rejects ambiguous scalar and list filters`);
}
for (const path of ["/api/v1/infrastructure/resources?", "/api/v1/operations/services?"]) {
  const all = await request(admin, ids, path);
  const sandbox = await request(admin, ids, path + "environments=SANDBOX");
  const prod = await request(admin, ids, path + "environments=PROD");
  const multiple = await request(admin, ids, path + "environments=SANDBOX&environments=PROD");
  check([all, sandbox, prod, multiple].every((row) => row.status === 200), `${path} accepts authorized adapter environment filters`);
  check(all.body.total > 0, `${path} starts with populated synthetic legacy adapter records`);
  check(sandbox.body.total <= multiple.body.total && prod.body.total <= multiple.body.total && multiple.body.total <= all.body.total, `${path} adapter totals remain scoped and bounded`);
  if (path.includes("/operations/")) check(prod.body.total > 0 && sandbox.body.total === 0, `${path} includes mapped PROD probes and excludes them from SANDBOX`);
}
const viewer = await login("uat-viewer-a");
const unauthorized = await request(viewer, [a], `/api/v1/unified/resources?organization_id=${b}&environments=SANDBOX`);
check(unauthorized.status === 403 || (unauthorized.status === 200 && !unauthorized.body.items?.length), "multi-environment selection does not grant another customer");
for (const [path, key] of [["/api/v1/infrastructure/resources", "resources"], ["/api/v1/operations/services", "services"]]) {
  const denied = await request(viewer, [a], `${path}?organization_id=${b}&environments=SANDBOX`);
  check(denied.status === 403 || (denied.status === 200 && !denied.body[key]?.length), `${path} environment selection cannot reveal another customer's adapter data`);
}
console.log(`RESULT ${checks} passed, 0 failed; isolated synthetic HTTP fixture`);
