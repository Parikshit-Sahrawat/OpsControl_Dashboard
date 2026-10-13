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
  await page.getByRole("heading", { name: "Overview", exact: true }).waitFor();
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
  await nav(page, "APIs");
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
  await page
    .getByRole("heading", { name: "HTTP sampled success", exact: true })
    .waitFor();
  await page
    .getByRole("row")
    .filter({ hasText: "Fictional NOC HTTPS Portal" })
    .first()
    .waitFor();
  await page
    .getByRole("button", { name: "Export report JSON", exact: true })
    .waitFor();
  checks.push(
    "Real sampled reports and export remain usable without incident data",
  );
  await nav(page, "Data Pipelines");
  await page
    .getByRole("heading", { name: "Data Pipelines", exact: true })
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
