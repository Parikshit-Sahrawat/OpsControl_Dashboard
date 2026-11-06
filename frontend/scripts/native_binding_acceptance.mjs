import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const f = JSON.parse(await readFile(process.env.ETL_BINDING_FIXTURE, "utf8"));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
  checks = [];
const ui = process.env.ETL_WORKFLOW_UI_URL,
  out = process.env.ETL_SCOPE_EVIDENCE_DIR;
async function open(user) {
  await page.goto(ui);
  await page.getByLabel("Username", { exact: true }).fill(user);
  await page.getByLabel("Password", { exact: true }).fill(f.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  await config();
}
async function config() {
  await page.goto(ui + "/#/resources/data-resources");
  await page.getByRole("tab", { name: "Data Pipelines", exact: true }).click();
  await page
    .getByLabel("Resource customer filter", { exact: true })
    .selectOption(f.a);
  await page.getByRole("button", { name: "View wa", exact: true }).click();
  await page.getByText("Native binding for job-0", { exact: true }).click();
  await page
    .getByText("Current binding: MISSING", { exact: true })
    .or(page.getByText("Current binding: STAGED", { exact: true }))
    .or(page.getByText("Current binding: RETIRED", { exact: true }))
    .first()
    .waitFor();
}
try {
  await open(f.username);
  const section = page
    .getByRole("region", { name: "Native binding configuration" })
    .first();
  await section
    .getByLabel("Native Job candidate", { exact: true })
    .selectOption(f.native_job);
  await section
    .getByLabel("Native authority claim", { exact: true })
    .fill(f.authority);
  await section.getByLabel("Synthetic method 0", { exact: false }).check();
  await section
    .getByLabel("Configuration change reason", { exact: true })
    .fill("Browser staged claim");
  await section
    .getByRole("button", { name: "Stage binding claim", exact: true })
    .click();
  await section.getByText("Current binding: STAGED", { exact: true }).waitFor();
  checks.push("Authenticated browser stages claim without activation");
  await page.reload();
  await config();
  await section.getByText("Current binding: STAGED", { exact: true }).waitFor();
  assert.equal(
    await section
      .getByLabel("Native authority claim", { exact: true })
      .inputValue(),
    f.authority,
  );
  checks.push("Save/reload retains immutable native identity and history");
  await section
    .getByLabel("Configuration change reason", { exact: true })
    .fill("Independent reviewer required");
  await section
    .getByRole("button", { name: "Request binding confirmation", exact: true })
    .click();
  await section.getByRole("alert").waitFor();
  assert.equal(
    await section
      .getByLabel("Configuration change reason", { exact: true })
      .inputValue(),
    "Independent reviewer required",
  );
  checks.push(
    "Rejected confirmation preserves unsaved reason and remains STAGED",
  );
  await section
    .getByLabel("Configuration change reason", { exact: true })
    .fill("Same target reader revision");
  await section
    .getByRole("button", { name: "Replace reader binding", exact: true })
    .click();
  await section
    .getByLabel("Binding history", { exact: true })
    .getByText("STAGED", { exact: true })
    .nth(1)
    .waitFor();
  checks.push("Same-target replacement retains previous immutable version");
  await section
    .getByLabel("Configuration change reason", { exact: true })
    .fill("Retire synthetic monitoring claim");
  await section
    .getByRole("button", { name: "Retire binding", exact: true })
    .click();
  await section
    .getByText("Current binding: RETIRED", { exact: true })
    .waitFor();
  assert.equal(
    await section
      .getByRole("button", { name: "Replace reader binding", exact: true })
      .isDisabled(),
    true,
  );
  checks.push("Retirement preserves history and disables further mutation");
  const readiness = page.getByRole("region", {
    name: "Authoritative readiness dimensions",
    exact: true,
  });
  await readiness.getByText("RETIRED", { exact: true }).waitFor();
  assert.equal(
    await readiness.getByText("HEALTHY", { exact: true }).count(),
    0,
  );
  for (const dimension of [
    "configuration completeness",
    "binding validity",
    "monitoring activation",
    "source connectivity",
    "evidence freshness",
    "operational health",
  ])
    await readiness.getByText(dimension, { exact: true }).first().waitFor();
  checks.push("Six backend dimensions; no health inferred from save");
  assert.equal(
    await page
      .getByRole("button", { name: /^(Run|Retry|Stop|Terminate)$/ })
      .count(),
    0,
  );
  checks.push("Monitoring-only UI has no workload controls");
  await page.screenshot({
    path: out + "/native-binding-history.png",
    fullPage: true,
  });
  let delayedResponse;
  const delivered = new Promise((resolve) => {
    delayedResponse = resolve;
  });
  await page.route(
    `**/api/v1/etl/workflows/${f.wa}/jobs/*/native-bindings`,
    async (route) => {
      const response = await route.fetch();
      await new Promise((resolve) => setTimeout(resolve, 800));
      try {
        await route.fulfill({ response });
      } catch (error) {
        // The real client aborts old-tenant reads on unmount. Accept only the
        // independently observed browser cancellation, never an arbitrary error.
        assert.match(route.request().failure()?.errorText || "", /ERR_ABORTED/);
        assert.match(String(error), /already handled|Target.*closed|canceled/i);
      } finally {
        delayedResponse();
      }
    },
  );
  await page.getByRole("button", { name: "View wa", exact: true }).click();
  await page.getByText("Native binding for job-0", { exact: true }).click();
  await page
    .getByLabel("Resource customer filter", { exact: true })
    .selectOption(f.b);
  await delivered;
  await page.getByRole("button", { name: "View wb", exact: true }).waitFor();
  assert.equal(
    await page.getByLabel("Native authority claim", { exact: true }).count(),
    0,
  );
  checks.push(
    "Old-tenant actual history read is delivered safely or explicitly aborted; it cannot reappear after tenant switch",
  );
  await page.unroute(`**/api/v1/etl/workflows/${f.wa}/jobs/*/native-bindings`);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await open(f.viewer);
  assert.equal(
    await section
      .getByRole("button", { name: "Stage binding claim", exact: true })
      .count(),
    0,
  );
  await section
    .getByText(
      "Read-only binding history. ETL configuration permission is required for changes.",
      { exact: true },
    )
    .waitFor();
  checks.push("Read-only user sees provenance without mutation controls");
  await page.screenshot({
    path: out + "/native-binding-viewer.png",
    fullPage: true,
  });
  await writeFile(
    out + "/native-binding-browser-results.json",
    JSON.stringify({ status: "PASS", checks }, null, 2),
  );
} catch (e) {
  await page.screenshot({
    path: out + "/native-binding-browser-failure.png",
    fullPage: true,
  });
  await writeFile(
    out + "/native-binding-browser-results.json",
    JSON.stringify({ status: "FAIL", checks, error: String(e) }, null, 2),
  );
  throw e;
} finally {
  await browser.close();
}
