import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  )
);
const fixture = JSON.parse(
  await readFile(
    join(process.env.V16_PRIVATE_DIR, "browser-fixture.json"),
    "utf8",
  ),
);
const out = process.env.V16_EVIDENCE_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : {}),
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const steps = [
  "General",
  "Platform",
  "Connection",
  "Integration",
  "Collection Sources",
  "Job Discovery/Selection",
  "Source Associations",
  "Validate & Activate",
];
async function navigate(target = page) {
  await target
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Resource Management", exact: true })
    .click();
  await target
    .getByRole("tab", { name: "Data Pipelines", exact: true })
    .click();
}
try {
  await page.goto(process.env.V16_UI_URL);
  await page.getByLabel("Username", { exact: true }).fill("v16-api-admin");
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  await navigate();
  const panel = page.getByRole("region", {
    name: "Data Pipelines integrations",
    exact: true,
  });
  await panel
    .getByRole("button", { name: "Create Data Pipeline", exact: true })
    .click();
  const wizard = page.getByRole("region", {
    name: "Data Pipelines eight-step wizard",
    exact: true,
  });
  const nav = wizard.getByRole("navigation", { name: "Data Pipeline steps" });
  assert.equal(await nav.getByRole("button").count(), 8);
  for (let i = 0; i < steps.length; i++)
    await nav
      .getByRole("button", { name: `${i + 1}. ${steps[i]}`, exact: true })
      .click();
  await nav.getByRole("button", { name: "1. General", exact: true }).click();
  const name = "Controlled browser draft " + Date.now();
  await wizard.getByLabel("Integration name", { exact: true }).fill(name);
  await wizard
    .getByLabel("Organization", { exact: true })
    .selectOption(fixture.organization_id);
  await nav.getByRole("button", { name: "2. Platform", exact: true }).click();
  await wizard
    .getByLabel("Platform family", { exact: true })
    .selectOption("AIRFLOW");
  await nav.getByRole("button", { name: "3. Connection", exact: true }).click();
  await wizard.getByLabel(/Base url/i).fill("https://airflow.example.test");
  const saved = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === "/api/v1/data-pipelines/integrations" &&
      r.request().method() === "POST",
  );
  await wizard
    .getByRole("button", { name: "Save / resume draft", exact: true })
    .click();
  const savedResponse = await saved;
  assert.equal(savedResponse.status(), 201);
  const integrationId = (await savedResponse.json()).id;
  await wizard
    .getByRole("button", { name: "Close configuration", exact: true })
    .click();
  await page.reload();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  await navigate();
  await panel.getByLabel("Search integrations", { exact: true }).fill(name);
  await panel.getByRole("button", { name, exact: true }).click();
  await wizard.getByLabel(/Base url/i).waitFor();
  assert.equal(
    await wizard.getByLabel(/Base url/i).inputValue(),
    "https://airflow.example.test",
  );
  // Continue the entire workflow through real APIs. Only vendor inventory is
  // fixture-driven by the owned test CLI; no runtime proof is manufactured.
  page.on("dialog", (dialog) => dialog.accept());
  async function mutateResponse(button, suffix) {
    const waiting = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname.endsWith(suffix) &&
        r.request().method() === "POST",
    );
    await button.click();
    const response = await waiting;
    assert.ok(response.ok(), `${suffix}: ${response.status()}`);
    const data = await response.json();
    await wizard
      .getByRole("button", { name: "Save / resume draft", exact: true })
      .waitFor({ state: "visible" });
    await wizard
      .getByRole("button", { name: "Save / resume draft", exact: true })
      .isEnabled();
    // The action refresh follows the mutation response. Wait for the control to
    // become enabled, rather than treating the HTTP response as a UI completion.
    await page.waitForFunction(() => {
      const root =
        document.querySelector(
          '[aria-label="Data Pipelines eight-step wizard"]',
        ) ||
        document.querySelector(
          '[aria-label="Data Pipeline eight-step wizard"]',
        );
      const buttons = root ? [...root.querySelectorAll("button")] : [];
      return buttons.some(
        (b) => b.textContent === "Save / resume draft" && !b.disabled,
      );
    });
    return data;
  }
  await wizard.getByLabel(/Auth type/i).fill("NONE");
  await wizard.getByLabel(/Dag id/i).fill("browser-native-job-A");
  await mutateResponse(
    wizard.getByRole("button", {
      name: "Save connection version",
      exact: true,
    }),
    "/connections",
  );
  await nav
    .getByRole("button", { name: "4. Integration", exact: true })
    .click();
  await wizard
    .getByLabel("platform version", { exact: true })
    .fill("2.10 fixture candidate");
  await mutateResponse(
    wizard.getByRole("button", {
      name: "Save capability profile",
      exact: true,
    }),
    "/capabilities",
  );
  await nav
    .getByRole("button", { name: "5. Collection Sources", exact: true })
    .click();
  const methods = [];
  for (const [label, scope] of [
    ["Browser API source A", "controlled-A"],
    ["Browser API source B", "controlled-B"],
  ]) {
    await wizard
      .getByLabel("Collection method name", { exact: true })
      .fill(label);
    await wizard
      .getByLabel("Source endpoint", { exact: true })
      .fill("https://airflow.example.test");
    await wizard
      .getByLabel("Source account", { exact: true })
      .fill("controlled-fixture");
    await wizard
      .getByLabel("Source physical scope", { exact: true })
      .fill(scope);
    methods.push(
      await mutateResponse(
        wizard.getByRole("button", {
          name: "Add collection method",
          exact: true,
        }),
        "/methods",
      ),
    );
  }
  assert.notEqual(methods[0].id, methods[1].id);
  assert.notEqual(methods[0].source_id, methods[1].source_id);
  await wizard
    .getByRole("columnheader", { name: /^method$/i })
    .waitFor();
  await page.screenshot({
    path: join(out, "pipeline-v16-methods.png"),
    fullPage: true,
  });
  await nav
    .getByRole("button", { name: "6. Job Discovery/Selection", exact: true })
    .click();
  const operation = await mutateResponse(
    wizard.getByRole("button", {
      name: "Discover jobs on demand",
      exact: true,
    }),
    "/discovery",
  );
  execFileSync(
    ".venv/bin/python",
    ["-m", "scripts.v16_browser_discovery", operation.id],
    {
      cwd: "backend",
      env: process.env,
      encoding: "utf8",
      timeout: 30000,
    },
  );
  await nav
    .getByRole("button", { name: "5. Collection Sources", exact: true })
    .click();
  await nav
    .getByRole("button", { name: "6. Job Discovery/Selection", exact: true })
    .click();
  const selectedRow = wizard
    .getByRole("row")
    .filter({ hasText: "browser-native-job-A" });
  await selectedRow.getByText("Not selected", { exact: true }).waitFor();
  const untouchedRow = wizard
    .getByRole("row")
    .filter({ hasText: "browser-native-job-B" });
  await untouchedRow.getByText("Not selected", { exact: true }).waitFor();
  const selection = await mutateResponse(
    selectedRow.getByRole("button", { name: "Select explicitly", exact: true }),
    "/selection",
  );
  await selectedRow.getByText("Selected", { exact: true }).waitFor();
  await untouchedRow.getByText("Not selected", { exact: true }).waitFor();
  await nav
    .getByRole("button", { name: "7. Source Associations", exact: true })
    .click();
  await wizard
    .getByLabel("Job association", { exact: true })
    .selectOption(selection.id);
  await wizard
    .getByLabel("Source association", { exact: true })
    .selectOption(methods[0].id);
  const association = await mutateResponse(
    wizard.getByRole("button", {
      name: "Confirm source association",
      exact: true,
    }),
    "/associations",
  );
  assert.equal(association.job_id, selection.id);
  assert.equal(association.method_id, methods[0].id);
  await wizard
    .getByRole("columnheader", { name: /^confirmation$/i })
    .waitFor();
  await nav
    .getByRole("button", { name: "8. Validate & Activate", exact: true })
    .click();
  const adminToken = await page.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const deniedActivation = await page.request.post(
    fixture.base_url +
      `/api/v1/data-pipelines/integrations/${integrationId}/activate`,
    {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: { idempotency_key: crypto.randomUUID(), confirmed: true },
    },
  );
  assert.equal(deniedActivation.status(), 409);
  assert.ok(
    JSON.stringify(await deniedActivation.json()).includes(
      "METHOD_NOT_RUNTIME_VERIFIED",
    ),
  );
  // Create an explicitly separate customer fixture, then test the scoped viewer
  // using a separate browser session and direct real HTTP authorization checks.
  const other = await page.request.post(
    fixture.base_url + "/api/v1/data-pipelines/integrations",
    {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        idempotency_key: crypto.randomUUID(),
        organization_id: fixture.other_organization_id,
        name: "Controlled browser other customer",
        platform: "AIRFLOW",
        environment: "TEST",
        configuration: {},
        stage: 1,
      },
    },
  );
  assert.equal(other.status(), 201);
  const otherId = (await other.json()).id;
  const viewer = await browser.newPage({
    viewport: { width: 1280, height: 900 },
  });
  await viewer.goto(process.env.V16_UI_URL);
  await viewer.getByLabel("Username", { exact: true }).fill("v16-api-viewer");
  await viewer
    .getByLabel("Password", { exact: true })
    .fill(fixture.viewer_password);
  await viewer.getByRole("button", { name: "Sign in", exact: true }).click();
  await viewer
    .getByRole("navigation", { name: "Primary navigation" })
    .waitFor();
  await navigate(viewer);
  const viewerPanel = viewer.getByRole("region", {
    name: "Data Pipelines integrations",
    exact: true,
  });
  await viewerPanel.getByRole("button", { name, exact: true }).waitFor();
  assert.equal(
    await viewerPanel
      .getByRole("button", { name: "Create Data Pipeline", exact: true })
      .count(),
    0,
  );
  const viewerToken = await viewer.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const headers = { Authorization: `Bearer ${viewerToken}` };
  const inventory = await viewer.request.get(
    fixture.base_url + "/api/v1/data-pipelines/integrations",
    { headers },
  );
  assert.equal(inventory.status(), 200);
  // Other HTTP probes may explicitly grant this viewer additional customers.
  // Verify the effective scope, then independently exercise the exact filter.
  const scopeResponse = await viewer.request.get(
    fixture.base_url + "/api/v1/auth/customer-scope", { headers },
  );
  assert.equal(scopeResponse.status(), 200);
  const authorized = new Set((await scopeResponse.json()).map(o => o.id));
  assert.ok((await inventory.json()).items.every(i => authorized.has(i.organization_id)));
  const scopedInventory = await viewer.request.get(
    fixture.base_url + "/api/v1/data-pipelines/integrations?organization_id=" + fixture.organization_id,
    { headers },
  );
  assert.equal(scopedInventory.status(), 200);
  assert.ok((await scopedInventory.json()).items.every(i => i.organization_id === fixture.organization_id));
  const crossCustomer = await viewer.request.get(
    fixture.base_url + `/api/v1/data-pipelines/integrations/${otherId}`,
    { headers },
  );
  assert.ok([403, 404].includes(crossCustomer.status()));
  const unauthorizedMutation = await viewer.request.post(
    fixture.base_url +
      `/api/v1/data-pipelines/integrations/${integrationId}/connections`,
    {
      headers,
      data: { idempotency_key: crypto.randomUUID(), configuration: {} },
    },
  );
  assert.equal(unauthorizedMutation.status(), 403);
  const unauthenticated = await viewer.request.get(
    fixture.base_url + "/api/v1/data-pipelines/integrations",
  );
  assert.equal(unauthenticated.status(), 401);
  await viewer.screenshot({
    path: join(out, "pipeline-v16-viewer.png"),
    fullPage: true,
  });
  await viewer.close();
  await nav
    .getByRole("button", { name: "8. Validate & Activate", exact: true })
    .click();
  assert.equal(
    await wizard
      .getByRole("button", { name: "Activate monitoring", exact: true })
      .isDisabled(),
    true,
  );
  await page.screenshot({
    path: join(out, "pipeline-v16-wizard.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 820 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    true,
  );
  await page.screenshot({
    path: join(out, "pipeline-v16-mobile.png"),
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  await writeFile(
    join(out, "browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        origin: "ACTUAL_PLAYWRIGHT_OWNED_API",
        steps: 8,
        clickable_steps: true,
        draft_connection_resume: true,
        unverified_activation_disabled: true,
        mobile_no_overflow: true,
        platform_connection_saved: true,
        independent_same_type_methods: 2,
        discovery_worker: "CONTROLLED_VENDOR_INVENTORY_FIXTURE",
        native_discovery_explicit_selection: true,
        unselected_job_preserved: true,
        confirmed_source_association: true,
        activation_denied_by_api: true,
        viewer_customer_isolation: true,
        viewer_mutation_denied_status: unauthorizedMutation.status(),
        cross_customer_denied_status: crossCustomer.status(),
        unauthenticated_denied_status: unauthenticated.status(),
        vendor_environments_accessed: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "V1.6 actual browser eight-step/draft/activation/mobile acceptance PASS",
  );
} catch (error) {
  await writeFile(
    join(process.env.V16_PRIVATE_DIR, "browser-failure.html"),
    await page.content(),
  );
  await page.screenshot({
    path: join(process.env.V16_PRIVATE_DIR, "browser-failure.png"),
    fullPage: true,
  });
  throw error;
} finally {
  await browser.close();
}
