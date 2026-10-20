import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";

// Creates fictional, inactive resources only in a disposable UAT-owned project.
const state = process.env.OPSCONTROL_UAT_STATE_DIR;
if (!state) throw new Error("OPSCONTROL_UAT_STATE_DIR is required");
const settings = JSON.parse(fs.readFileSync(path.join(state, "settings.json"), "utf8"));
if (!settings.project?.startsWith("opscontrol-s14-uat-")) throw new Error("UAT-owned project required");
const users = JSON.parse(fs.readFileSync(path.join(state, "uat-users.json"), "utf8"));
users["demo-admin"] = fs.readFileSync(path.join(state, "admin-password"), "utf8").trim();
const base = `http://127.0.0.1:${settings.api_port}`;
let checks = 0;
function check(condition, label) { assert.ok(condition, label); checks++; console.log(`PASS ${label}`); }
async function login(username) {
  const response = await fetch(base + "/api/v1/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password: users[username] }) });
  assert.equal(response.status, 200, `login ${username}`);
  return (await response.json()).access_token;
}
async function request(token, customers, pathname, payload) {
  const response = await fetch(base + pathname, {
    method: payload ? "POST" : "GET",
    headers: { Authorization: `Bearer ${token}`, "X-OpsControl-Customers": customers.join(","), ...(payload ? { "Content-Type": "application/json" } : {}) },
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  });
  return { status: response.status, body: await response.json() };
}
const admin = await login("demo-admin");
const scope = await request(admin, [], "/api/v1/auth/customer-scope");
assert.equal(scope.status, 200);
const a = scope.body.find((row) => row.code === "UAT-A")?.id;
const b = scope.body.find((row) => row.code === "UAT-B")?.id;
check(Boolean(a && b), "two fictional customer IDs available");
const suffix = randomUUID().slice(0, 8);
const cases = [
  { domain: "VM", customer: a, environment: "SANDBOX" },
  { domain: "VM", customer: b, environment: "DEV" },
  { domain: "API", customer: a, environment: "SANDBOX" },
  { domain: "API", customer: b, environment: "DEV" },
];
for (const item of cases) {
  item.name = `UAT-filter-${suffix}-${item.domain}-${item.environment}`;
  item.sourceName = item.domain === "VM" ? item.name.toLowerCase() : item.name;
  const payload = item.domain === "VM"
    ? { name: item.name, hostname: item.name.toLowerCase(), address: `${item.name.toLowerCase()}.example.test`, os_type: "Linux", environment: item.environment, organization_id: item.customer, active: false }
    : { name: item.name, dns: `${item.name.toLowerCase()}.example.test`, environment: item.environment, organization_id: item.customer, active: false };
  const created = await request(admin, [item.customer], `/api/v1/unified/resources/${item.domain.toLowerCase()}`, payload);
  check(created.status === 201 && created.body.id, `${item.domain} ${item.environment} synthetic resource created through authorized API`);
}
for (const [domain, endpoint, key] of [["VM", "/api/v1/infrastructure/resources", "resources"], ["API", "/api/v1/operations/services", "services"]]) {
  const get = async (token, customers, filter) => request(token, customers, `${endpoint}?${filter}`);
  const sandbox = await get(admin, [a, b], "environments=SANDBOX");
  const dev = await get(admin, [a, b], "environments=DEV");
  const union = await get(admin, [a, b], "environments=SANDBOX&environments=DEV");
  check([sandbox, dev, union].every((row) => row.status === 200), `${domain} environment queries succeed`);
  const [sandboxName, devName] = cases.filter((item) => item.domain === domain).map((item) => item.sourceName);
  check(sandbox.body[key].some((row) => row.name === sandboxName) && !sandbox.body[key].some((row) => row.name === devName), `${domain} SANDBOX includes only its matching new source`);
  check(dev.body[key].some((row) => row.name === devName) && !dev.body[key].some((row) => row.name === sandboxName), `${domain} DEV includes only its matching new source`);
  check(union.body[key].some((row) => row.name === sandboxName) && union.body[key].some((row) => row.name === devName), `${domain} union includes both environment records`);
  const viewer = await login("uat-viewer-a");
  const restricted = await get(viewer, [a], "environments=SANDBOX&environments=DEV");
  check(restricted.status === 200 && restricted.body[key].some((row) => row.name === sandboxName) && !restricted.body[key].some((row) => row.name === devName), `${domain} multi-environment selection cannot reveal Customer B to Customer A viewer`);
}
console.log(`RESULT ${checks} passed, 0 failed; fictional inactive resources in disposable PostgreSQL only`);
