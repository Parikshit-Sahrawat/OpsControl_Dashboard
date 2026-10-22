// Real browser regression for retained NOC evidence; no incident/ITSM workflow.
import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const state = JSON.parse(await readFile(process.env.ETL_SESSION_FILE, "utf8")),
  phase = process.argv[2],
  out = process.env.OPERATIONAL_EVIDENCE_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
});
const errors = [],
  checks = [];
async function login(who) {
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1100 },
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:15174");
  await page
    .getByLabel("Username", { exact: true })
    .fill(state[who + "_username"]);
  await page
    .getByLabel("Password", { exact: true })
    .fill(state[who + "_password"]);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
  return page;
}
async function nav(page, name) {
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name, exact: true })
    .click();
}
try {
  const page = await login("reader");
  assert.equal(
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Incidents", exact: true })
      .count(),
    0,
  );
  await page.locator(".org-context-button").click();
  const organizations = page.locator(".org-menu");
  assert.equal(await organizations.getByText("Other ETL Tenant").count(), 0);
  await organizations
    .getByRole("checkbox", { name: /Controlled ETL Lab/ })
    .check();
  await nav(page, "API Endpoint Monitoring");
  const showProbes = page.getByRole("button", { name: "Show service probe health", exact: true });
  await page.getByRole("button", { name: /^(Show|Hide) service probe health$/ }).waitFor();
  if (await showProbes.isVisible()) await showProbes.click();
  await page.getByRole("button", { name: "Hide service probe health", exact: true }).waitFor();
  const service = page
    .getByTestId("service-row")
    .filter({ hasText: "Fictional NOC HTTPS Portal" });
  await service.waitFor();
  assert.ok(
    (await service.textContent()).includes(
      phase === "failed"
        ? "CRITICAL"
        : phase === "recovered"
          ? "HEALTHY"
          : "HEALTHY",
    ),
  );
  await page.getByLabel("Search services").fill("Fictional NOC");
  assert.equal(await page.getByTestId("service-row").count(), 1);
  checks.push("Actual service evidence, health and search filter");
  await nav(page, "Alerts");
  if (phase !== "configured") {
    await page
      .locator("tbody")
      .getByText(/noc-http-unavailable/)
      .first()
      .waitFor();
    const buttons = page.getByRole("button", {
      name: "Acknowledge",
      exact: true,
    });
    for (let i = 0; i < (await buttons.count()); i++)
      assert.equal(await buttons.nth(i).isDisabled(), true);
  }
  checks.push(
    "Independent monitoring alerts render; reader cannot acknowledge",
  );
  await nav(page, "Reports");
  const reportResponse = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === "/api/v1/unified/reports/API" &&
      r.request().method() === "GET",
  );
  await page
    .getByRole("tab", { name: "API Endpoint Reports", exact: true })
    .click();
  const report = await (await reportResponse).json();
  assert(
    report.summary.completed_probes > 0,
    "Reports must contain actual completed probe evidence",
  );
  const reportResource = `Fictional NOC HTTPS Portal · PROD · ${state.http_source_id}`;
  await page
    .locator(`#report-resource-choices option[value="${reportResource}"]`)
    .waitFor({ state: "attached" });
  const filteredResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === "/api/v1/unified/reports/API" &&
      url.searchParams.getAll("resource_id").includes(state.http_source_id);
  });
  await page.getByLabel("Report resource").fill(reportResource);
  const filteredReport = await (await filteredResponse).json();
  assert.deepEqual(filteredReport.resources.map((row) => row.id), [state.http_source_id]);
  assert(filteredReport.summary.completed_probes > 0);
  await page
    .getByRole("button", { name: "Export JSON", exact: true })
    .waitFor();
  checks.push(
    "Real sampled reports and export remain usable without incident data",
  );
  await nav(page, "Data Pipeline Monitoring");
  await page
    .getByRole("heading", { name: "Pipeline Inventory", exact: true })
    .waitFor();
  checks.push("Data pipeline execution screen remains functional");
  await page.screenshot({ path: out + "/" + phase + ".png", fullPage: true });
  assert.deepEqual(errors, []);
  await writeFile(
    out + "/browser-" + phase + ".json",
    JSON.stringify({ status: "PASS", checks, page_errors: errors }, null, 2) +
      "\n",
  );
  console.log("NOC ALERT / REPORT / PIPELINE BROWSER PASS " + phase);
} finally {
  await browser.close();
}
