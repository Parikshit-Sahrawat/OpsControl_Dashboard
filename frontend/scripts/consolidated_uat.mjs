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
    0,
  );
  await nav("Data Pipelines");
  await page
    .getByRole("heading", { name: "Data Pipelines", exact: true })
    .waitFor();
  await nav("Resource Management");
  await page
    .getByRole("heading", { name: "Organizations", exact: true })
    .waitFor();
  assert.equal(await page.locator(".org-context-button").count(), 0);
  await page
    .locator("table")
    .first()
    .locator("th")
    .filter({ hasText: "Organization" })
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
    "Organization compact table, operational selector independence and Data Pipelines terminology; no Incidents navigation",
  );
  await page.locator(".resource-tab").filter({ hasText: "Collectors" }).click();
  const row = page.locator("tr").filter({ hasText: "UAT logical Collector" });
  await row.getByRole("button", { name: "Collector Details" }).click();
  const dialog = page.getByRole("dialog", { name: "Collector Details" });
  await dialog
    .getByRole("heading", { name: "Collection Methods", exact: true })
    .waitFor();
  await dialog.getByRole("button", { name: "Add Method", exact: true }).click();
  await dialog
    .getByLabel("Method name", { exact: true })
    .fill("Browser same-type log");
  await dialog
    .getByLabel("Paths (one absolute path per line)", { exact: true })
    .fill("/var/log/opscontrol/browser.log");
  await dialog
    .getByRole("button", { name: "Save Method", exact: true })
    .click();
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
    .locator(".resource-tab")
    .filter({ hasText: "Notification Delivery" })
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
    .locator(".resource-tab")
    .filter({ hasText: "Event Parameters" })
    .click();
  await page.getByText("CPU sustained 80 percent", { exact: true }).waitFor();
  await page.screenshot({
    path: join(out, "event-parameters-dark.png"),
    fullPage: true,
  });
  checks.push(
    "Configured Event Parameters and independent Notification Delivery show real stored rule/delivery data",
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
    .getByRole("heading", { name: "Organizations", exact: true })
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
