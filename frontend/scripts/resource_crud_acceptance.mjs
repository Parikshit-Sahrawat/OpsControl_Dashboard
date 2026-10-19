import { scopeHeaders } from "./explicit_scope.mjs";
// Actual browser forms and authenticated backend; no mocked API responses.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [],
  serverErrors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("response", (r) => {
  if (r.url().includes("/api/") && r.status() >= 500)
    serverErrors.push(r.status());
});
const base = process.env.TEST_API_BASE;
const password = "testing-only-StrongPassword-123!";
let phase = "login";
try {
  await page.goto(process.env.RELEASE_UI_BASE);
  await page.getByLabel("Username").fill("test-north");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Overview", exact: true }).waitFor();
  phase = "open onboarding";
  await page
    .getByRole("button", { name: "Data Sources / Resources", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create Compute Instance", exact: true })
    .click();
  let modal = page.getByRole("dialog", {
    name: "Create Compute Instance",
    exact: true,
  });
  await modal
    .getByLabel("Resource name", { exact: true })
    .fill("Wizard sequence registration");
  const customerOption = modal
    .getByLabel("Customer", { exact: true })
    .locator("option")
    .nth(1);
  await modal
    .getByLabel("Customer", { exact: true })
    .selectOption(await customerOption.getAttribute("value"));
  await modal.getByLabel(/^Environment/).selectOption("DEV");
  await modal
    .getByLabel("Hostname", { exact: true })
    .fill("wizard-sequence.example.test");
  await modal
    .getByLabel("DNS / IP address", { exact: true })
    .fill("203.0.113.75");
  await modal
    .getByRole("button", { name: "Save resource identity", exact: true })
    .click();
  await modal
    .getByRole("heading", { name: "Collector Configuration", exact: true })
    .waitFor();
  await modal
    .getByRole("button", { name: "Close resource form", exact: true })
    .click();
  phase = "locate created resource";
  await page
    .getByLabel("Search resources", { exact: true })
    .fill("Wizard sequence registration");
  let row = page
    .getByRole("row")
    .filter({ hasText: "Wizard sequence registration" });
  await row.waitFor();
  const token = await page.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const headers = await scopeHeaders(page.request, base, token);
  const sourcesResponse = await page.request.get(
    base + "/api/v1/resource-management/data-sources",
    { headers },
  );
  assert.equal(sourcesResponse.status(), 200);
  const source = (await sourcesResponse.json()).find(
    (s) => s.name === "wizard-sequence.example.test",
  );
  assert.ok(source);
  const collectorPath =
    base + "/api/v1/resource-management/collectors?data_source_id=" + source.id;
  let registrations = await (
    await page.request.get(collectorPath, { headers })
  ).json();
  assert.equal(registrations.length, 1);
  const registration = registrations[0];
  assert.equal(registration.collector_type, "OTEL");
  assert.equal(registration.enabled, true);
  assert.equal(registration.status, "STOPPED");
  assert.equal(
    registration.name,
    "Wizard sequence registration Agent Configuration",
  );
  const duplicate = await page.request.post(
    base + "/api/v1/resource-management/data-sources",
    {
      headers,
      data: {
        organization_id: source.organization_id,
        name: source.name,
        source_type: source.source_type,
      },
    },
  );
  assert.equal(duplicate.status(), 409);
  phase = "edit registration";
  await row
    .getByRole("button", { name: "Collector Configuration", exact: true })
    .click();
  modal = page.getByRole("dialog", { name: "Collector Details", exact: true });
  await modal
    .getByLabel("Collector name", { exact: true })
    .fill("wizard-registration-updated");
  await modal
    .getByRole("button", { name: "Save Collector Details", exact: true })
    .click();
  await modal
    .getByRole("button", { name: "Close Collector Details", exact: true })
    .click();
  phase = "verify persisted registration";
  await modal.waitFor({ state: "hidden" });
  registrations = await (
    await page.request.get(collectorPath, { headers })
  ).json();
  assert.equal(registrations.length, 1);
  assert.equal(registrations[0].id, registration.id);
  assert.equal(registrations[0].name, "wizard-registration-updated");
  assert.equal(registrations[0].enabled, true);
  const runs = await page.request.get(
    base + "/api/v1/monitoring/collectors/" + registration.id + "/runs",
    { headers },
  );
  assert.deepEqual(await runs.json(), []);
  const otherLogin = await page.request.post(base + "/api/v1/auth/login", {
    data: { username: "test-south", password },
  });
  assert.equal(otherLogin.status(), 200);
  const otherHeaders = await scopeHeaders(
    page.request,
    base,
    (await otherLogin.json()).access_token,
  );
  const cross = await page.request.patch(
    base + "/api/v1/resource-management/data-sources/" + source.id,
    {
      headers: otherHeaders,
      data: { name: "forged-cross-tenant" },
    },
  );
  assert.equal(cross.status(), 404);
  const crossRows = await page.request.get(collectorPath, {
    headers: otherHeaders,
  });
  assert.deepEqual(await crossRows.json(), []);
  phase = "overlapping refresh ordering";
  // Delay an unchanged, authenticated backend response; no fabricated rows.
  // A second refresh must win even when the first snapshot arrives last.
  let signalCaptured, releaseOlder;
  const captured = new Promise((resolve) => {
    signalCaptured = resolve;
  });
  const held = new Promise((resolve) => {
    releaseOlder = resolve;
  });
  let finishOlder;
  const finishedOlder = new Promise((resolve) => {
    finishOlder = resolve;
  });
  let olderError;
  let first = true;
  const inventoryRoute = "**/api/v1/unified/resources?*";
  await page.route(inventoryRoute, async (route) => {
    if (!first) return route.continue();
    first = false;
    const response = await route.fetch();
    signalCaptured();
    await held;
    try {
      await route.fulfill({ response });
    } catch (error) {
      // Changing the search aborts the superseded fetch. Both abort and a late
      // response must leave the newer persisted inventory visible.
      if (route.request().failure()?.errorText !== "net::ERR_ABORTED")
        olderError = error;
    } finally {
      finishOlder();
    }
  });
  try {
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await captured;
    const inventory = await (
      await page.request.get(
        base +
          "/api/v1/unified/resources?domain=VM&search=Wizard%20sequence%20registration",
        { headers },
      )
    ).json();
    const resource = inventory.items.find(
      (r) => r.data_source_id === source.id,
    );
    assert(resource);
    const renamed = "Wizard sequence refreshed";
    const updated = await page.request.put(
      base + "/api/v1/unified/resources/" + resource.id,
      {
        headers,
        data: {
          expected_revision: resource.revision,
          name: renamed,
          environment: resource.environment,
          configuration: resource.configuration,
          active: resource.active,
        },
      },
    );
    assert.equal(updated.status(), 200);
    await page
      .getByLabel("Search resources", { exact: true })
      .fill("Wizard sequence");
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await page.getByRole("button", { name: renamed, exact: true }).waitFor();
    releaseOlder();
    await page.waitForLoadState("networkidle");
    assert.equal(
      await page.getByRole("button", { name: renamed, exact: true }).count(),
      1,
    );
  } finally {
    releaseOlder();
    await finishedOlder;
    await page.unroute(inventoryRoute);
    if (olderError) throw olderError;
  }
  await mkdir(process.env.RELEASE_EVIDENCE_DIR, { recursive: true });
  await page.screenshot({
    path: process.env.RELEASE_EVIDENCE_DIR + "/resource-registration.png",
    fullPage: true,
  });
  phase = "disable resource";
  row = page.getByRole("row").filter({ hasText: "Wizard sequence refreshed" });
  await row.getByRole("button", { name: "Edit", exact: true }).click();
  modal = page.getByRole("dialog", {
    name: "Edit Compute Instance",
    exact: true,
  });
  await modal.getByLabel("Enable resource", { exact: true }).uncheck();
  await modal
    .getByRole("button", { name: "Save resource", exact: true })
    .click();
  await modal.waitFor({ state: "hidden" });
  const disabled = (
    await (
      await page.request.get(
        base +
          "/api/v1/unified/resources?domain=VM&search=Wizard%20sequence%20refreshed",
        { headers },
      )
    ).json()
  ).items.find((r) => r.data_source_id === source.id);
  assert.equal(disabled.active, false);
  assert.deepEqual(errors, []);
  assert.deepEqual(serverErrors, []);
  await writeFile(
    process.env.RELEASE_EVIDENCE_DIR + "/resource-crud.json",
    JSON.stringify(
      {
        status: "PASS",
        checks: [
          "Browser create/read/update/disable persisted",
          "Duplicate source returns 409",
          "Logical OTEL configuration creates no polling CollectorRun",
          "Edit preserves Collector ID and updates its configuration name",
          "Other tenant cannot read registration or mutate source",
          "Older authenticated inventory refresh cannot overwrite newer persisted state",
        ],
        page_errors: errors,
        server_errors: serverErrors,
      },
      null,
      2,
    ),
  );
  console.log(
    "RESOURCE WIZARD / INACTIVE REGISTRATION / CRUD / TENANT ACCEPTANCE PASS",
  );
} catch (error) {
  // Only a fixture phase and error type leave the private diagnostics directory.
  console.error(
    "RESOURCE_CRUD_FAILURE " + JSON.stringify({ phase, type: error.name }),
  );
  throw error;
} finally {
  await browser.close();
}
