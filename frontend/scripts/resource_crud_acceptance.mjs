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
    .getByRole("button", { name: "Resource Management", exact: true })
    .click();
  await page
    .getByRole("button", { name: "+ Add Data Source", exact: true })
    .click();
  let modal = page.getByRole("dialog", {
    name: "Add Data Source",
    exact: true,
  });
  await modal.getByRole("button", { name: "Next: Data Source →" }).click();
  await modal
    .getByLabel("Host Name", { exact: true })
    .fill("wizard-sequence.example.test");
  await modal
    .getByLabel("Visible Name", { exact: true })
    .fill("Wizard sequence registration");
  await modal.getByRole("button", { name: "Next: Templates →" }).click();
  await modal
    .getByRole("button", { name: "Next: Collector Configuration →" })
    .click();
  await modal
    .getByLabel("Collector name", { exact: true })
    .fill("wizard-registration");
  await modal.getByRole("button", { name: "Review", exact: true }).click();
  await modal
    .getByRole("button", {
      name: "Create Data Source + Collector",
      exact: true,
    })
    .click();
  phase = "locate created resource";
  await modal.waitFor({ state: "hidden" });
  await page
    .locator(".resource-summary-card")
    .filter({ hasText: "Data Sources" })
    .click();
  // Exercise the real filter before editing/capturing the created resource.
  // Capturing all 400+ seeded rows produced a 27,838px screenshot and made
  // this unrelated CRUD gate depend on runner rasterization performance.
  await page
    .getByPlaceholder("Search hostname, role, product...")
    .fill("wizard-sequence.example.test");
  let row = page
    .getByRole("row")
    .filter({ hasText: "Wizard sequence registration" });
  await row.waitFor();
  const token = await page.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const headers = { Authorization: "Bearer " + token };
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
  assert.equal(registration.name, "wizard-registration");
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
  await row.getByRole("button", { name: "Edit", exact: true }).click();
  modal = page.getByRole("dialog", { name: "Edit Data Source", exact: true });
  await modal.getByRole("button", { name: "Next: Data Source →" }).click();
  await modal.getByRole("button", { name: "Next: Templates →" }).click();
  await modal
    .getByRole("button", { name: "Next: Collector Configuration →" })
    .click();
  assert.equal(
    await modal.getByLabel("Collector name", { exact: true }).inputValue(),
    "wizard-registration",
  );
  await modal
    .getByLabel("Collector name", { exact: true })
    .fill("wizard-registration-updated");
  await modal.getByRole("button", { name: "Review", exact: true }).click();
  await modal
    .getByRole("button", { name: "Save Data Source", exact: true })
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
  const otherHeaders = {
    Authorization: "Bearer " + (await otherLogin.json()).access_token,
  };
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
  let first = true;
  const inventoryRoute = "**/api/v1/resource-management/data-sources?*";
  await page.route(inventoryRoute, async (route) => {
    if (!first) return route.continue();
    first = false;
    const response = await route.fetch();
    signalCaptured();
    await held;
    await route.fulfill({ response });
  });
  try {
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await captured;
    const renamed = "wizard-sequence-refreshed.example.test";
    const updated = await page.request.patch(
      base + "/api/v1/resource-management/data-sources/" + source.id,
      {
        headers,
        data: { name: renamed },
      },
    );
    assert.equal(updated.status(), 200);
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await page
      .locator("b")
      .filter({ hasText: "Wizard sequence registration" })
      .waitFor();
    await page.locator('b[title="' + renamed + '"]').waitFor();
    releaseOlder();
    await page.waitForLoadState("networkidle");
    assert.equal(await page.locator('b[title="' + renamed + '"]').count(), 1);
  } finally {
    releaseOlder();
    await page.unroute(inventoryRoute);
  }
  await mkdir(process.env.RELEASE_EVIDENCE_DIR, { recursive: true });
  await page.screenshot({
    path: process.env.RELEASE_EVIDENCE_DIR + "/resource-registration.png",
    fullPage: true,
  });
  phase = "disable resource";
  page.once("dialog", (dialog) => dialog.accept());
  row = page
    .getByRole("row")
    .filter({ hasText: "Wizard sequence registration" });
  await row.getByRole("button", { name: "Disable", exact: true }).click();
  await row
    .getByRole("button", { name: "Disable", exact: true })
    .waitFor({ state: "hidden" });
  const disabled = (
    await (
      await page.request.get(
        base + "/api/v1/resource-management/data-sources",
        { headers },
      )
    ).json()
  ).find((s) => s.id === source.id);
  assert.equal(disabled.enabled, false);
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
