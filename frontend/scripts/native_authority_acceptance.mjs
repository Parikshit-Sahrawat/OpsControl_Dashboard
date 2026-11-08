import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const f = JSON.parse(
  await readFile(process.env.ETL_AUTHORITY_BROWSER_FIXTURE, "utf8"),
);
const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}) }),
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
  checks = [];
const out = process.env.ETL_SCOPE_EVIDENCE_DIR,
  api = process.env.ETL_SCOPE_API_URL;
try {
  await page.goto(process.env.ETL_WORKFLOW_UI_URL);
  await page.getByLabel("Username", { exact: true }).fill(f.username);
  await page.getByLabel("Password", { exact: true }).fill(f.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  await page.goto(
    process.env.ETL_WORKFLOW_UI_URL + "/#/resources/data-resources",
  );
  await page.getByRole("tab", { name: "Data Pipelines", exact: true }).click();
  await page
    .getByLabel("Resource customer filter", { exact: true })
    .selectOption(f.a);
  await page.getByRole("button", { name: "View wa", exact: true }).click();
  await page.getByText("Native binding for job-0", { exact: true }).click();
  const native = page
    .getByRole("region", { name: "Native binding configuration", exact: true })
    .first();
  await native.getByText("Current binding: STAGED", { exact: true }).waitFor();
  await native
    .getByText("No qualified native-authority attestation is available.", {
      exact: true,
    })
    .waitFor();
  checks.push("Live scoped UI shows staged claim and no qualified authority");
  const response = await page.request.post(
    api + "/api/v1/etl/native-authority/validate-envelope",
    {
      headers: {
        Authorization: "Bearer " + f.token,
        "X-OpsControl-Customers": f.a,
      },
      data: { envelope: f.envelope },
    },
  );
  assert.equal(response.status(), 200);
  const result = await response.json();
  assert.equal(result.qualified, false);
  assert.equal(result.status, "CONTRACT_VALID_NOT_QUALIFIED");
  assert.equal(result.persisted, false);
  checks.push(
    "Actual browser HTTP validates signature contract only, without provider qualification",
  );
  await native
    .getByLabel("Configuration change reason", { exact: true })
    .fill("Test envelope does not confer monitoring authority");
  const denied = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" && r.url().endsWith("/native-bindings"),
  );
  await native
    .getByRole("button", { name: "Request binding confirmation", exact: true })
    .click();
  assert.equal((await denied).status(), 403);
  await native.getByRole("alert").waitFor();
  await native.getByText("Current binding: STAGED", { exact: true }).waitFor();
  checks.push("Self confirmation refuses and preserves the staged version");
  const dimensions = page.getByRole("region", {
    name: "Authoritative readiness dimensions",
    exact: true,
  });
  await dimensions.getByText("BLOCKED", { exact: true }).first().waitFor();
  assert.equal(
    await dimensions.getByText("HEALTHY", { exact: true }).count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("button", { name: /^(Run|Retry|Stop|Terminate)$/ })
      .count(),
    0,
  );
  checks.push("Readiness remains blocked/unverified with no workload controls");
  await page.screenshot({
    path: out + "/authority-unqualified-browser.png",
    fullPage: true,
  });
  await writeFile(
    out + "/authority-browser-results.json",
    JSON.stringify(
      {
        status: "PASS_CONTRACT_AND_DENIAL_ONLY",
        checks,
        provider_qualified: false,
      },
      null,
      2,
    ),
  );
} catch (e) {
  await page.screenshot({
    path: out + "/authority-browser-failure.png",
    fullPage: true,
  });
  throw e;
} finally {
  await browser.close();
}
