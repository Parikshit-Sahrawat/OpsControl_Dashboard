import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  )
);
const f = JSON.parse(
  await readFile(
    join(process.env.V16_PRIVATE_DIR, "sprint09-fixture.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
});
const page = await browser.newPage({ viewport: { width: 1400, height: 960 } }),
  errors = [],
  checks = [];
page.setDefaultTimeout(25000);
page.on("pageerror", (e) => errors.push(e.message));
async function shot(name) {
  await page.screenshot({
    path: join(process.env.V16_EVIDENCE_DIR, "sprint09-" + name + ".png"),
    fullPage: true,
  });
}
async function route(key) {
  await page.goto(process.env.V16_UI_URL + "/#/pipelines/" + key);
}
try {
  await page.addInitScript(
    (id) =>
      localStorage.setItem("opscontrol.organizationIds", JSON.stringify([id])),
    f.organization,
  );
  await route("inventory");
  await page.getByLabel("Username", { exact: true }).fill(f.username);
  await page.getByLabel("Password", { exact: true }).fill(f.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", {name:"Pipeline Inventory",exact:true}).waitFor();
  await page.getByRole("navigation", {name:"Pipeline operational pages"}).getByRole("link", {name:"Execution History",exact:true}).click();
  await page.getByRole("heading", {name:"Execution History",exact:true}).waitFor();
  await page
    .getByLabel("Find pipeline", { exact: true })
    .fill("Sprint 09 archive pipeline");
  await page
    .getByRole("button", { name: "Search pipelines", exact: true })
    .click();
  await page
    .getByRole("option", { name: /Sprint 09 archive pipeline/ })
    .waitFor({ state: "attached" });
  await page
    .getByLabel("Selected pipeline", { exact: true })
    .selectOption(f.resource);
  const result = page.waitForResponse(
    (r) => r.url().includes("outcome=SUCCESS") && r.status() === 200,
  );
  await page.getByLabel("Execution outcome").selectOption("SUCCESS");
  const body = await (await result).json();
  assert.equal(body.total, 1);
  await page
    .getByRole("region", { name: "Execution history", exact: true })
    .getByRole("button", { name: f.history, exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Execution details",
    exact: true,
  });
  await dialog.getByRole("button", { name: "Audit", exact: true }).click();
  const retained = page.getByRole("region", {
    name: "Retained attempt evidence",
  });
  await retained.getByLabel("Evidence collection").selectOption("aliases");
  await retained
    .getByText(/INVOCATION/)
    .first()
    .waitFor();
  await retained
    .getByRole("navigation", { name: "Retained evidence pagination" })
    .getByRole("button", { name: "Next page" })
    .click();
  await retained
    .getByRole("navigation", { name: "Retained evidence pagination" })
    .getByText(/21–40 of/)
    .waitFor();
  await shot("attempt-archive");
  checks.push(
    "Server outcome filtering and paginated retained attempt aliases in the real execution drawer",
  );
  await dialog
    .getByRole("button", { name: "Close detail drawer", exact: true })
    .click();
  await route("schedules");
  await page
    .getByRole("heading", { name: "Schedule Monitoring", exact: true })
    .waitFor();
  await page
    .getByLabel("Selected pipeline", { exact: true })
    .selectOption(f.resource);
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText(/of 603/)
    .waitFor();
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByRole("button", { name: "Next page" })
    .click();
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText(/21–40 of 603/)
    .waitFor();
  const filtered = page.waitForResponse(
    (r) =>
      r.url().includes("schedule-occurrences") &&
      r.url().includes("status=NO_RUN") &&
      r.status() === 200,
  );
  await page.getByLabel("Schedule compliance").selectOption("NO_RUN");
  assert.equal((await (await filtered).json()).total, 0);
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText("0–0 of 0", { exact: true })
    .waitFor();
  await shot("schedule-filter");
  checks.push(
    "Schedule paging and server filter keep unknown/incomplete fixture coverage out of NO_RUN",
  );
  await route("incidents");
  await page
    .getByRole("region", { name: "Native incident correlation" })
    .getByRole("button")
    .first()
    .click();
  const incident = page.getByRole("dialog", {
    name: "Incident correlation details",
    exact: true,
  });
  await incident.getByRole("button", { name: "Audit", exact: true }).click();
  await incident
    .getByRole("navigation", { name: "Activities pagination" })
    .getByRole("button", { name: "Next page" })
    .click();
  await incident
    .getByRole("navigation", { name: "Activities pagination" })
    .getByText(/21–40 of/)
    .waitFor();
  await shot("incident-activity");
  checks.push(
    "Native incident activity history pages without alternate lifecycle definitions",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    join(process.env.V16_EVIDENCE_DIR, "sprint09-browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        backend: "Actual local authenticated API and owned PostgreSQL",
        genuine_runtime_acceptance: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "Sprint 09 actual Chromium archive acceptance PASS:",
    checks.length,
    "groups",
  );
} finally {
  await browser.close();
}
