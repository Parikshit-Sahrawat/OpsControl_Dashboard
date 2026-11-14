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


// APTron foundation: existing resource authority also governs each domain route.
test("domain inventories retain explicit role guards and legacy bookmarks", async () => {
  const { visibleFoundationSections } = await import("../src/foundationNavigation.js");
  for (const [section, path] of [["compute-instances", "#/resources/compute-instances"], ["data-pipelines", "#/resources/data-pipelines"], ["apis", "#/resources/apis"]]) {
    assert.deepEqual(readSectionRoute(path, user(["resources.view"])), ["Resource Management", section]);
    assert.equal(readSectionRoute(path, user(["alerts.view"])), null);
    assert.equal(canOpenSection(user([]), "Resource Management", section), false);
  }
  assert.deepEqual(readSectionRoute("#/resources/data-resources", user(["resources.view"])), ["Resource Management", "resources"]);
  assert.deepEqual(visibleFoundationSections(user([])), []);
  const rolesOnly = { roles: ["administrator"] };
  assert.deepEqual(visibleFoundationSections(rolesOnly), []);
  const operator = visibleFoundationSections(user(["alerts.view"]));
  assert.deepEqual(operator.map(g => g.items), [[["Alerts", "Alerts"]]]);
  for (const principal of [{ platform_admin: true }, user(["incidents.view"]), user(["alerts.view", "resources.view"])]) {
    assert.equal(visibleFoundationSections(principal).flatMap(g => g.items).some(([page]) => page === "Incidents"), false);
  }
});
