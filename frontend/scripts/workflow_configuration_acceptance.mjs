import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const fixture = JSON.parse(await readFile(process.env.ETL_UI_FIXTURE, "utf8"));
const out = process.env.ETL_SCOPE_EVIDENCE_DIR,
  base = process.env.ETL_SCOPE_API_URL,
  ui = process.env.ETL_WORKFLOW_UI_URL;
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
  checks = [],
  errors = [];
page.on("pageerror", (err) => errors.push(err.name));
const region = () =>
  page.getByRole("region", { name: "ETL Workflow configuration", exact: true });
async function login(name) {
  await page.goto(ui);
  await page.getByLabel("Username", { exact: true }).fill(name);
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
}
async function configuration(customer) {
  if (page.url() !== ui + "/#/resources/data-resources") await page.goto(ui + "/#/resources/data-resources");
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  await page.getByRole("tab", { name: "Data Pipelines", exact: true }).click();
  await page
    .getByLabel("Resource customer filter", { exact: true })
    .selectOption(customer);
  await region()
    .getByRole("heading", { name: "ETL Workflows", exact: true })
    .waitFor();
}
async function expectText(text) {
  await region().getByText(text, { exact: true }).first().waitFor();
}
async function open(name) {
  await region()
    .getByRole("button", { name: "View " + name, exact: true })
    .click();
  await region().getByRole("heading", { name, exact: true }).waitFor();
}
async function saveWorkflow() {
  await region()
    .getByRole("button", { name: "Save Workflow", exact: true })
    .click();
  await region()
    .getByText(
      "Configuration saved. This does not establish operational health.",
      { exact: true },
    )
    .waitFor();
}
try {
  await login(fixture.username);
  await configuration(fixture.a);
  await open("wa");
  await expectText("STALE");
  await expectText("MISSING");
  await expectText("BLOCKED");
  await expectText("UNVERIFIED");
  checks.push(
    "Backend persisted stale/missing telemetry distinguished from blocked activation and unverified provider",
  );
  await region()
    .getByRole("button", { name: "Create Workflow", exact: true })
    .click();
  await region()
    .getByLabel("Workflow name", { exact: true })
    .fill("UI workflow");
  await region()
    .getByLabel("Expected start window", { exact: true })
    .fill("08:00");
  await region()
    .getByLabel("Expected end window", { exact: true })
    .fill("10:00");
  await region()
    .getByLabel("Workflow SLA seconds", { exact: true })
    .fill("900");
  await region()
    .getByLabel("Workflow expected duration seconds", { exact: true })
    .fill("500");
  await region().getByLabel("Timezone", { exact: true }).fill("UTC");
  await saveWorkflow();
  checks.push("Workflow created through secured actual API");
  const token = (
    await (
      await page.request.post(base + "/api/v1/auth/login", {
        data: { username: fixture.username, password: fixture.password },
      })
    ).json()
  ).access_token;
  const headers = {
    Authorization: "Bearer " + token,
    "X-OpsControl-Customers": fixture.a,
  };
  const invalidTimezone = await page.request.patch(
    base + "/api/v1/etl/workflows/" + fixture.wa,
    { headers, data: { timezone: "Not/AZone" } },
  );
  assert.equal(invalidTimezone.status(), 422);
  assert.equal((await invalidTimezone.json()).detail, "Invalid input");
  checks.push(
    "Backend independently rejects invalid timezone and retains error redaction",
  );
  let rows = await (
    await page.request.get(
      base + "/api/v1/etl/workflows?organization_id=" + fixture.a,
      { headers },
    )
  ).json();
  const workflow = rows.find((row) => row.name === "UI workflow");
  assert.ok(workflow);
  await region()
    .getByRole("button", { name: "Edit Workflow", exact: true })
    .click();
  await region()
    .getByLabel("Workflow name", { exact: true })
    .fill("UI workflow edited");
  await saveWorkflow();
  checks.push("Workflow edit persists");
  await page.reload();
  await configuration(fixture.a);
  await open("UI workflow edited");
  await region()
    .getByRole("button", { name: "Edit Workflow", exact: true })
    .click();
  assert.equal(
    await region()
      .getByLabel("Workflow SLA seconds", { exact: true })
      .inputValue(),
    "900",
  );
  assert.equal(
    await region()
      .getByLabel("Expected start window", { exact: true })
      .inputValue(),
    "08:00",
  );
  assert.equal(
    await region()
      .getByLabel("Workflow expected duration seconds", { exact: true })
      .inputValue(),
    "500",
  );
  await region()
    .getByRole("button", { name: "Cancel Workflow edit", exact: true })
    .click();
  checks.push("Full reload restores Workflow configuration");
  for (const name of ["UI job one", "UI job two"]) {
    await region()
      .getByRole("button", { name: "Add Job", exact: true })
      .click();
    await region().getByLabel("Job name", { exact: true }).fill(name);
    await region()
      .getByLabel("Host identity", { exact: true })
      .fill("ui-host.synthetic.invalid");
    await region()
      .getByLabel("Expected runtime seconds", { exact: true })
      .fill("120");
    await region()
      .getByRole("button", { name: "Save Job", exact: true })
      .click();
    await region()
      .getByRole("button", { name: "Edit Job " + name, exact: true })
      .waitFor();
  }
  await expectText("VALID");
  await expectText("BLOCKED");
  checks.push(
    "Child Jobs persisted in parent; valid supported configuration remains activation BLOCKED",
  );
  await region()
    .getByRole("button", { name: "Edit Job UI job one", exact: true })
    .click();
  assert.equal(
    await region().getByLabel("Workflow SLA seconds", { exact: true }).count(),
    0,
  );
  await region()
    .getByLabel("Expected runtime seconds", { exact: true })
    .fill("150");
  const savedRuntime = page.waitForResponse(
    (response) =>
      response.request().method() === "PATCH" &&
      /\/etl\/workflows\/[^/]+\/jobs\/[^/]+$/.test(
        new URL(response.url()).pathname,
      ),
  );
  await region().getByRole("button", { name: "Save Job", exact: true }).click();
  const savedRuntimeResponse = await savedRuntime;
  assert.equal(savedRuntimeResponse.status(), 200);
  assert.equal(
    (await savedRuntimeResponse.json()).expected_duration_seconds,
    150,
  );
  await page.reload();
  await configuration(fixture.a);
  await open("UI workflow edited");
  await region()
    .getByRole("button", { name: "Edit Job UI job one", exact: true })
    .click();
  assert.equal(
    await region()
      .getByLabel("Expected runtime seconds", { exact: true })
      .inputValue(),
    "150",
  );
  await region()
    .getByRole("button", { name: "Cancel Job edit", exact: true })
    .click();
  checks.push("Job runtime edit/reload without Workflow timing duplication");
  const jobs = await (
    await page.request.get(
      base + "/api/v1/etl/workflows/" + workflow.id + "/jobs",
      { headers },
    )
  ).json();
  const a = jobs.find((j) => j.name === "UI job one").id,
    b = jobs.find((j) => j.name === "UI job two").id;
  await region().getByLabel("Predecessor Job", { exact: true }).selectOption(a);
  await region().getByLabel("Successor Job", { exact: true }).selectOption(b);
  await region()
    .getByRole("button", { name: "Save dependency", exact: true })
    .click();
  await expectText("UI job one → UI job two");
  await region().getByLabel("Predecessor Job", { exact: true }).selectOption(b);
  await region().getByLabel("Successor Job", { exact: true }).selectOption(a);
  await region()
    .getByRole("button", { name: "Save dependency", exact: true })
    .click();
  await expectText("Workflow dependency cycle");
  checks.push(
    "Actual backend DAG cycle rejection displayed after persisted dependency",
  );
  await region().getByLabel("Predecessor Job", { exact: true }).selectOption(a);
  await region().getByLabel("Successor Job", { exact: true }).selectOption(b);
  await region()
    .getByRole("button", { name: "Save dependency", exact: true })
    .click();
  await expectText("Dependency already exists");
  checks.push("Duplicate dependency has actionable UI validation");
  await region().getByLabel("Predecessor Job", { exact: true }).selectOption(b);
  await region().getByLabel("Successor Job", { exact: true }).selectOption(b);
  await region()
    .getByRole("button", { name: "Save dependency", exact: true })
    .click();
  await expectText("A Job cannot depend on itself");
  checks.push("Self dependency prevented");
  await region()
    .getByRole("button", { name: "Edit Workflow", exact: true })
    .click();
  await region().getByLabel("Timezone", { exact: true }).fill("Not/AZone");
  await region()
    .getByRole("button", { name: "Save Workflow", exact: true })
    .click();
  await region()
    .getByRole("alert")
    .filter({ hasText: /timezone/i })
    .waitFor();
  assert.equal(
    await region().getByLabel("Timezone", { exact: true }).inputValue(),
    "Not/AZone",
  );
  await region().getByLabel("Timezone", { exact: true }).fill("UTC");
  await region()
    .getByLabel("Workflow name", { exact: true })
    .fill("Unsaved draft");
  await page.route("**/api/v1/etl/workflows/" + workflow.id, (route) =>
    route.request().method() === "PATCH"
      ? route.abort("failed")
      : route.continue(),
  );
  await region()
    .getByRole("button", { name: "Save Workflow", exact: true })
    .click();
  await region().getByRole("alert").waitFor();
  assert.equal(
    await region().getByLabel("Workflow name", { exact: true }).inputValue(),
    "Unsaved draft",
  );
  await page.unroute("**/api/v1/etl/workflows/" + workflow.id);
  await region()
    .getByLabel("Workflow name", { exact: true })
    .fill("UI workflow edited");
  await saveWorkflow();
  checks.push(
    "Invalid backend input and injected network save failure preserve unsaved fields; retry succeeds",
  );
  await page.screenshot({
    path: out + "/workflow-desktop.png",
    fullPage: true,
  });
  await page
    .getByLabel("Resource environment filter", { exact: true })
    .selectOption("QA");
  assert.equal(
    await region()
      .getByRole("button", { name: "View UI workflow edited", exact: true })
      .count(),
    0,
  );
  await page
    .getByLabel("Resource environment filter", { exact: true })
    .selectOption("PROD");
  await region()
    .getByRole("button", { name: "View UI workflow edited", exact: true })
    .waitFor();
  checks.push("Environment filter excludes other configuration");
  let release, started, delivered;
  const deliveredResponse = new Promise((resolve) => {
    delivered = resolve;
  });
  const waiting = new Promise((resolve) => {
      started = resolve;
    }),
    gate = new Promise((resolve) => {
      release = resolve;
    });
  await page.route(
    "**/api/v1/etl/workflows/" + workflow.id + "/monitoring",
    async (route) => {
      const response = await route.fetch();
      started();
      await gate;
      try {
        await route.fulfill({ response });
      } catch {
        /* Request may be cancelled by tenant switch. */
      } finally {
        delivered();
      }
    },
  );
  await region()
    .getByRole("button", { name: "View UI workflow edited", exact: true })
    .click();
  await waiting;
  await page
    .getByLabel("Resource customer filter", { exact: true })
    .selectOption(fixture.b);
  release();
  await deliveredResponse;
  await region()
    .getByRole("button", { name: "View wb", exact: true })
    .waitFor();
  assert.equal(
    await region()
      .getByRole("heading", { name: "UI workflow edited", exact: true })
      .count(),
    0,
  );
  await page.unroute("**/api/v1/etl/workflows/" + workflow.id + "/monitoring");
  checks.push(
    "Delayed real response from old tenant cannot hydrate new tenant",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await open("wb");
  assert.ok(
    (await region().boundingBox()).width <= 390,
    "Workflow region must fit mobile width",
  );
  await page.screenshot({ path: out + "/workflow-mobile.png", fullPage: true });
  checks.push("Mobile configuration renders accessible controls");
  const viewer = (
    await (
      await page.request.post(base + "/api/v1/auth/login", {
        data: { username: fixture.viewer, password: fixture.password },
      })
    ).json()
  ).access_token;
  const vh = {
    Authorization: "Bearer " + viewer,
    "X-OpsControl-Customers": fixture.a,
  };
  assert.equal(
    (
      await page.request.get(base + "/api/v1/etl/workflows/" + workflow.id, {
        headers: vh,
      })
    ).status(),
    200,
  );
  assert.equal(
    (
      await page.request.patch(base + "/api/v1/etl/workflows/" + workflow.id, {
        headers: vh,
        data: { name: "forbidden" },
      })
    ).status(),
    403,
  );
  assert.ok(
    [403, 404].includes(
      (
        await page.request.get(base + "/api/v1/etl/workflows/" + fixture.wb, {
          headers: vh,
        })
      ).status(),
    ),
  );
  checks.push(
    "Actual authenticated viewer read succeeds, mutation/cross-tenant access denied",
  );
  assert.equal(
    (
      await page.request.post(
        base + "/api/v1/etl/workflows/" + workflow.id + "/dependencies",
        {
          headers,
          data: { predecessor_job_id: a, successor_job_id: fixture.j1 },
        },
      )
    ).status(),
    409,
  );
  checks.push("Cross-workflow Job reference rejected");
  assert.equal(
    (
      await page.request.patch(base + "/api/v1/etl/workflows/" + workflow.id, {
        headers,
        data: { environment: "QA" },
      })
    ).status(),
    409,
  );
  checks.push("Backend rejects changing populated Workflow environment");
  assert.equal(
    await region()
      .getByRole("button", { name: /^(Run|Retry|Stop|Terminate)$/ })
      .count(),
    0,
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(fixture.viewer);
  await configuration(fixture.a);
  await open("UI workflow edited");
  assert.equal(
    await region()
      .getByRole("button", { name: "Create Workflow", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await region()
      .getByRole("button", { name: "Edit Workflow", exact: true })
      .count(),
    0,
  );
  assert.equal(
    await region()
      .getByRole("button", { name: "Add Job", exact: true })
      .count(),
    0,
  );
  await expectText("900 seconds");
  await expectText("500 seconds");
  await expectText("08:00–10:00");
  checks.push(
    "Authenticated read-only role sees evidence without configuration controls",
  );
  await page.screenshot({ path: out + "/workflow-viewer.png", fullPage: true });
  assert.equal(errors.length, 0);
  checks.push("Monitoring-only controls; zero browser runtime errors");
  await writeFile(
    out + "/workflow-browser-results.json",
    JSON.stringify(
      {
        status: "PASS",
        checks,
        provider_certification: false,
        independent_uat: false,
      },
      null,
      2,
    ) + "\n",
  );
  console.log("Authenticated Workflow browser PASS:", checks.length, "groups");
} catch (error) {
  await page.screenshot({
    path: out + "/workflow-failure.png",
    fullPage: true,
  });
  console.error(error);
  throw error;
} finally {
  await browser.close();
}
