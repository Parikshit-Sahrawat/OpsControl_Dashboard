import test from "node:test";
import assert from "node:assert/strict";
import {
  hasPermission,
  canNavigate,
  administrationPage,
  parseCustomerSelection,
} from "../src/permissions.js";
const user = {
  permissions: ["access.view", "resources.view"],
  customer_permissions: { a: ["resources.view"], b: ["alerts.view"] },
};
test("navigation and customer actions default deny", () => {
  assert.equal(canNavigate({}, "Access Management"), false);
  assert.equal(canNavigate(user, "Access Management"), true);
  assert.equal(hasPermission(user, "resources.view", "a"), true);
  assert.equal(hasPermission(user, "resources.view", "b"), false);
  assert.equal(canNavigate(user, "Unknown Page"), false);
});
test("administrative pages use independent filters", () => {
  assert.equal(administrationPage("Access Management"), true);
  assert.equal(administrationPage("Resource Management"), true);
  for (const page of [
    "Overview",
    "Data Pipeline Monitoring",
    "Compute Health",
    "API Endpoint Monitoring",
    "Alerts",
    "Reports",
  ])
    assert.equal(administrationPage(page), false);
});
test("revocation replaces UI affordances; platform capability is explicit", () => {
  assert.equal(
    canNavigate({ ...user, permissions: [] }, "Access Management"),
    false,
  );
  assert.equal(
    hasPermission({ roles: ["platform-administrator"] }, "access.manage_users"),
    false,
  );
  assert.equal(
    hasPermission({ platform_admin: true }, "access.manage_users"),
    true,
  );
});

test("malformed cached customer preferences cannot corrupt selector state", () => {
  for (const raw of ["{}", "42", "null", "broken-json"])
    assert.deepEqual(parseCustomerSelection(raw), []);
  assert.deepEqual(parseCustomerSelection('["a",null,17,"a","b"]'), ["a", "b"]);
});

test("retired navigation cannot be enabled by cached permissions", () => {
  for (const page of [
    "ETL Monitoring",
    "VM Health",
    "API Monitoring",
    "Monitoring Setup",
    "Organizations",
    "Collectors",
  ])
    assert.equal(canNavigate({ platform_admin: true }, page), false);
  assert.equal(
    canNavigate({ permissions: ["etl.view"] }, "Data Pipeline Monitoring"),
    true,
  );
});

test("retired incident UI cannot be opened even with incident permission", () => {
  assert.equal(canNavigate({ platform_admin: true }, "Incidents"), false);
  assert.equal(canNavigate({}, "Incidents"), false);
  assert.equal(
    canNavigate({ permissions: ["incidents.view"] }, "Incidents"),
    false,
  );
});

import { sessionWasRejected } from "../src/sessionVerification.js";
test("only authoritative authentication rejection invalidates a token; transport remains fail-closed", () => {
  assert.equal(sessionWasRejected({status:401}), true);
  assert.equal(sessionWasRejected({status:403}), true);
  for (const error of [{name:"AbortError"},{status:500},new TypeError("network unavailable"),null]) assert.equal(sessionWasRejected(error),false);
});
