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
    "ETL Monitoring",
    "VM Health",
    "API Monitoring",
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
  for (const page of ["Incidents", "Monitoring Setup", "Organizations", "Collectors"])
    assert.equal(canNavigate({platform_admin: true}, page), false);
  assert.equal(canNavigate({permissions:["etl.view"]}, "ETL Monitoring"), true);
});
