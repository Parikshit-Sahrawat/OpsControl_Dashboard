import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE);
const root = process.env.UAT_PRIVATE_DIR,
  out = process.env.UAT_EVIDENCE_DIR,
  ui = process.env.UAT_UI_URL;
const fixture = JSON.parse(
  await readFile(join(root, "browser-fixture.json"), "utf8"),
);
const password = (
  await readFile(process.env.UAT_ADMIN_PASSWORD_FILE, "utf8")
).trim();
await mkdir(out, { recursive: true });
const errors = [],
  checks = [];
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
  args: [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--ignore-certificate-errors-spki-list=" + process.env.UAT_TLS_SPKI,
  ],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  ignoreHTTPSErrors: false,
  reducedMotion: "reduce",
});
const page = await context.newPage();
let apiOrigin = "";
page.on("response", (response) => {
  if (new URL(response.url()).pathname === "/api/v1/auth/login")
    apiOrigin = new URL(response.url()).origin;
});
page.on("pageerror", (e) => errors.push(e.message));
page.on("dialog", (dialog) => dialog.accept());
const nav = async (name) => {
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name, exact: true })
    .click();
};
const waitFor = async (fn, label = "condition") => {
  for (let i = 0; i < 100; i++) {
    if (await fn()) return;
    await page.waitForTimeout(100);
  }
  throw new Error("Browser condition timed out: " + label);
};
try {
  await page.addInitScript(() =>
    localStorage.setItem("opscontrol.theme", "dark"),
  );
  await page.goto(ui);
  await page.getByLabel("Username", { exact: true }).fill("uat-admin");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  assert.equal(
    await page.evaluate(() => document.documentElement.dataset.theme),
    "dark",
  );
  assert.equal(
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Incidents", exact: true })
      .count(),
    1,
  );
  await nav("Data Pipeline Monitoring");
  await page
    .getByRole("heading", { name: "Data Pipeline Monitoring", exact: true })
    .waitFor();
  await nav("Resource Management");
  await page
    .getByRole("heading", { name: "Compute Instances", exact: true })
    .waitFor();
  assert.equal(await page.locator(".org-context-button").count(), 0);
  await page
    .locator("table")
    .first()
    .locator("th")
    .filter({ hasText: "Customer" })
    .waitFor();
  await page.screenshot({
    path: join(out, "organizations-dark.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  assert.equal(
    await page.evaluate(() => document.documentElement.dataset.theme),
    "light",
  );
  await page.screenshot({
    path: join(out, "organizations-light.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Dark theme", exact: true }).click();
  checks.push(
    "Compute compact table, customer selector independence, official terminology and native Incidents navigation",
  );
  assert(
    ["localhost", "127.0.0.1"].includes(new URL(apiOrigin).hostname),
    "UAT mutations must target the owned local API",
  );
  const inventory = await page.evaluate(
    async (input) => {
      const r = await fetch(
        input.origin +
          "/api/v1/unified/resources?domain=VM&organization_id=" +
          input.organization +
          "&limit=200",
        {
          headers: {
            Authorization:
              "Bearer " + sessionStorage.getItem("opscontrol.sessionToken"),
          },
        },
      );
      if (!r.ok) throw Error("UAT resource inventory failed");
      return r.json();
    },
    { origin: apiOrigin, organization: fixture.organization },
  );
  const compute = inventory.items.find(
    (r) =>
      r.data_source_id === fixture.source_id &&
      r.primary_collector_id === fixture.collector_id,
  );
  assert(
    compute,
    "The fixture must preserve its real Agent Source/Collector IDs under a scoped Compute resource binding",
  );
  await page.getByLabel("Search resources", { exact: true }).fill(compute.name);
  const row = page.getByRole("row").filter({ hasText: compute.name });
  const collectorResponse = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname ===
        "/api/v1/agent-control/collectors/" + fixture.collector_id &&
      r.request().method() === "GET",
  );
  await row
    .getByRole("button", { name: "Collector Configuration", exact: true })
    .click();
  const initialCollector = await (await collectorResponse).json();
  assert(
    initialCollector.methods.filter((m) => m.method_type === "FILE_LOG")
      .length >= 2,
    "Fixture must preserve multiple independent real File Log methods",
  );
  const dialog = page.getByRole("dialog", {
    name: "Collector Details",
    exact: true,
  });
  await dialog
    .getByRole("heading", { name: "Collection Methods", exact: true })
    .waitFor();
  await dialog.getByRole("button", { name: "Add Method", exact: true }).click();
  await dialog
    .getByLabel("Method name", { exact: true })
    .fill("Browser same-type log");
  await dialog
    .getByLabel("Paths", { exact: true })
    .fill(JSON.stringify(["/var/log/opscontrol/browser.log"]));
  const methodResponse = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname ===
        "/api/v1/agent-control/collectors/" +
          fixture.collector_id +
          "/methods" && r.request().method() === "POST",
  );
  await dialog
    .getByRole("button", { name: "Save Method", exact: true })
    .click();
  const savedMethodResponse = await methodResponse;
  assert.equal(savedMethodResponse.status(), 201);
  const savedMethod = await savedMethodResponse.json();
  assert(!initialCollector.methods.some((m) => m.id === savedMethod.id));
  await dialog.getByText("Browser same-type log", { exact: true }).waitFor();
  const methodRow = dialog
    .locator("tr")
    .filter({ hasText: "Browser same-type log" });
  await methodRow.getByRole("button", { name: "Disable", exact: true }).click();
  await waitFor(async () => (await methodRow.textContent()).includes("No"));
  await methodRow.getByRole("button", { name: "Edit", exact: true }).click();
  assert.equal(
    await dialog.getByLabel("Method name", { exact: true }).inputValue(),
    "Browser same-type log",
  );
  await dialog
    .getByRole("button", { name: "Cancel Method", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Preview YAML", exact: true })
    .click();
  await dialog.locator(".configuration-preview").waitFor();
  assert.ok(
    (await dialog.locator(".configuration-preview").textContent()).includes(
      "otlphttp/opscontrol",
    ),
  );
  assert.ok(
    !(await dialog.locator(".configuration-preview").textContent()).includes(
      "Browser same-type log",
    ),
  );
  assert(
    !(await dialog.locator(".configuration-preview").textContent()).includes(
      "filelog/" + savedMethod.id.replaceAll("-", ""),
    ),
    "Disabled method receiver must be absent from actual YAML pipelines",
  );
  await dialog.evaluate((node) => {
    node.scrollTop = 0;
  });
  await page.screenshot({
    path: join(out, "collector-methods-dark.png"),
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Close Collector Details" }).click();
  checks.push(
    "Real same-type method add/edit/disable; correct inherited OS, real signal counters and YAML excludes disabled method",
  );
  await page
    .getByRole("tab", { name: "Notification Delivery", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Notification Delivery", exact: true })
    .waitFor();
  await page.getByText("UAT in-app", { exact: true }).waitFor();
  await page.screenshot({
    path: join(out, "notification-delivery-dark.png"),
    fullPage: true,
  });
  await page
    .getByRole("tab", { name: "Event Parameters", exact: true })
    .click();
  await page
    .getByRole("tab", { name: "Compute Health Parameters", exact: true })
    .click();
  await page.getByRole("button", { name: compute.name, exact: true }).click();
  const parameterEditor = page.locator(".unified-parameters");
  await parameterEditor
    .getByLabel("Observed metric", { exact: true })
    .locator("option")
    .nth(1)
    .waitFor({ state: "attached" });
  const metricOption = parameterEditor
    .getByLabel("Observed metric", { exact: true })
    .locator("option")
    .filter({ hasText: /cpu/i })
    .first();
  await parameterEditor
    .getByLabel("Observed metric", { exact: true })
    .selectOption(await metricOption.getAttribute("value"));
  await parameterEditor
    .getByLabel("Critical threshold", { exact: true })
    .fill("80");
  await parameterEditor
    .getByRole("button", { name: "Add metric threshold", exact: true })
    .click();
  const savedParameter = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname ===
        "/api/v1/unified/parameters/" + compute.id &&
      r.request().method() === "POST",
  );
  await parameterEditor
    .getByRole("button", { name: "Save version", exact: true })
    .click();
  const parameterResponse = await savedParameter;
  assert.equal(parameterResponse.status(), 201);
  const parameterVersion = await parameterResponse.json();
  assert.equal(parameterVersion.configuration.thresholds.at(-1).critical, 80);
  assert.equal(
    parameterVersion.configuration.thresholds.at(-1).metric_definition_id,
    await metricOption.getAttribute("value"),
  );
  await page.screenshot({
    path: join(out, "event-parameters-dark.png"),
    fullPage: true,
  });
  checks.push(
    "Resource-scoped Event Parameter version preserves its actual CPU series and threshold; independent Notification Delivery shows real stored destinations",
  );
  await nav("Access Management");
  await page
    .getByRole("button", {
      name: "Guided Department → Employee → Permissions",
      exact: true,
    })
    .click();
  const guide = page.getByRole("dialog", {
    name: "Department Employee Permissions onboarding",
  });
  await guide
    .getByLabel("Select existing department")
    .selectOption(fixture.department_id);
  await guide.getByRole("button", { name: "Continue to Employee" }).click();
  await guide
    .getByLabel("Full name", { exact: true })
    .fill("Browser UAT Employee");
  await guide
    .getByLabel("Username", { exact: true })
    .fill("browser-uat-employee");
  await guide.getByLabel("Initial password", { exact: true }).fill(password);
  await guide
    .getByRole("button", { name: "Create Employee", exact: true })
    .click();
  await guide.getByLabel("Search existing employees").waitFor();
  await guide
    .getByLabel("Search existing employees")
    .fill("Browser UAT Employee");
  await waitFor(
    async () =>
      (await guide
        .getByLabel("Employee", { exact: true })
        .locator("option")
        .filter({ hasText: "Browser UAT Employee" })
        .count()) === 1,
    "employee selector",
  );
  const employeeOption = guide
    .getByLabel("Employee", { exact: true })
    .locator("option")
    .last();
  await guide
    .getByLabel("Employee", { exact: true })
    .selectOption(await employeeOption.getAttribute("value"));
  await guide
    .getByRole("heading", { name: "Effective permissions", exact: true })
    .waitFor();
  await guide.getByRole("button", { name: "Finish", exact: true }).click();
  await page.screenshot({
    path: join(out, "access-workflow-dark.png"),
    fullPage: true,
  });
  checks.push(
    "Real guided Department→Employee→Permissions workflow and searchable existing employee selector",
  );
  await page
    .getByRole("button", { name: "Collapse sidebar", exact: true })
    .click();
  await waitFor(
    async () =>
      await page.evaluate(
        () => document.documentElement.dataset.sidebar === "collapsed",
      ),
  );
  assert.equal(
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Alerts", exact: true })
      .count(),
    1,
  );
  await nav("Alerts");
  await page.getByRole("heading", { name: "Alerts", exact: true }).waitFor();
  await page
    .locator("tbody")
    .getByText("RESOLVED", { exact: true })
    .first()
    .waitFor();
  await page
    .getByRole("button", { name: "Expand sidebar", exact: true })
    .click();
  await page.setViewportSize({ width: 390, height: 844 });
  await nav("Resource Management");
  await page
    .getByRole("heading", { name: "Compute Instances", exact: true })
    .waitFor();
  assert.ok(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 2,
    ),
    "Page has uncontrolled horizontal overflow",
  );
  await page.screenshot({
    path: join(out, "organizations-mobile.png"),
    fullPage: true,
  });
  checks.push(
    "Accessible collapsed icon navigation, monitoring Alerts and mobile overflow containment",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    join(out, "browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        page_errors: errors,
        screenshots: [
          "organizations-dark.png",
          "collector-methods-dark.png",
          "notification-delivery-dark.png",
          "event-parameters-dark.png",
          "access-workflow-dark.png",
          "organizations-mobile.png",
        ],
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    "CONSOLIDATED REAL BROWSER UAT PASS (" + checks.length + " groups)",
  );
} catch (error) {
  await writeFile(
    join(out, "browser-failure.json"),
    JSON.stringify(
      {
        status: "FAIL",
        message: error.message,
        checks,
        page_errors: errors,
        visible_headings: await page.locator("h2,h3").allTextContents(),
        employee_options: await page
          .locator("select")
          .evaluateAll((nodes) =>
            nodes.flatMap((node) =>
              [...node.options].map((option) => option.text),
            ),
          ),
      },
      null,
      2,
    ),
  );
  throw error;
} finally {
  await browser.close();
}
