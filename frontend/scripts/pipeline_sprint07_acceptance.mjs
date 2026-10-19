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
    join(process.env.V16_PRIVATE_DIR, "sprint07-fixture.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
});
const checks = [],
  errors = [],
  out = process.env.V16_EVIDENCE_DIR;
let inspected;
const pages = {
  inventory: "Pipeline Inventory",
  executions: "Execution History",
  schedules: "Schedule Monitoring",
  evidence: "Evidence Review",
  recovery: "Recovery Tracking",
  incidents: "Incident Correlation",
};
async function session(username) {
  const p = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  inspected = p;
  p.setDefaultTimeout(25000);
  p.on("pageerror", (e) => errors.push(e.message));
  await p.addInitScript(
    (id) =>
      localStorage.setItem("opscontrol.organizationIds", JSON.stringify([id])),
    f.organization,
  );
  await p.goto(process.env.V16_UI_URL + "/#/pipelines/inventory");
  await p.getByLabel("Username", { exact: true }).fill(username);
  await p.getByLabel("Password", { exact: true }).fill(f.password);
  await p.getByRole("button", { name: "Sign in", exact: true }).click();
  await p
    .getByRole("heading", { name: pages.inventory, exact: true })
    .waitFor();
  return p;
}
async function route(p, key) {
  await p
    .getByRole("navigation", { name: "Pipeline operational pages" })
    .getByRole("link", { name: pages[key], exact: true })
    .click();
  await p.getByRole("heading", { name: pages[key], exact: true }).waitFor();
}
async function search(p, value = "Orders") {
  await p.getByLabel("Find pipeline", { exact: true }).fill(value);
  await p
    .getByRole("button", { name: "Search pipelines", exact: true })
    .click();
  await p
    .getByRole("navigation", { name: "Pipelines pagination" })
    .getByText("1–1 of 1", { exact: true })
    .waitFor();
  if (value === "Orders") {
    const selected = p.getByLabel("Selected pipeline", { exact: true });
    if (await selected.count()) await selected.selectOption(f.resource);
    else {
      await p
        .getByRole("button", { name: "Orders Pentaho", exact: true })
        .click();
      await close(p);
    }
  }
}
async function close(p) {
  await p
    .getByRole("button", { name: "Close detail drawer", exact: true })
    .click();
}
async function screenshot(p, name) {
  await p.screenshot({
    path: join(out, "sprint07-" + name + ".png"),
    fullPage: true,
  });
}
async function request(p, path, body, expected) {
  const token = await p.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const r = await p.request.post(process.env.V16_API_URL + path, {
    headers: {
      Authorization: "Bearer " + token,
      "X-OpsControl-Customers": f.organization,
    },
    data: body,
  });
  if (expected) assert.equal(r.status(), expected, await r.text());
  else assert.ok(r.ok(), await r.text());
  return r.json();
}
async function decide(p, label) {
  const form = p.getByRole("form", { name: label, exact: true });
  await form.waitFor();
  const reason = form.getByLabel("Decision reason", { exact: true });
  if (await reason.count())
    await reason.fill("Controlled browser review of verified native evidence");
  await form.getByRole("checkbox").check();
  const button = form.getByRole("button", { name: label, exact: true });
  await button.waitFor();
  const response = p.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().includes("/api/v1/"),
  );
  await button.click();
  const r = await response;
  assert.ok(r.ok(), await r.text());
}
async function recovery(p) {
  await route(p, "recovery");
  await p
    .getByRole("region", { name: "Recovery execution selection", exact: true })
    .getByRole("row")
    .filter({ hasText: f.original })
    .getByRole("button", { name: "Track recovery" })
    .click();
  await p
    .getByRole("heading", { name: "Original failed execution", exact: true })
    .waitFor();
}
async function switchCustomer(p, from, to) {
  await p.locator(".org-context-button").click();
  await p.getByRole("checkbox", { name: new RegExp(to) }).check();
  await p.getByRole("checkbox", { name: new RegExp(from) }).uncheck();
  await p.locator(".org-context-button").click();
}
let page;
try {
  page = await session(f.operator);
  const pager = page.getByRole("navigation", { name: "Pipelines pagination" });
  await pager.getByText("1–20 of 23", { exact: true }).waitFor();
  await pager.getByRole("button", { name: "Next page" }).click();
  await pager.getByText("21–23 of 23", { exact: true }).waitFor();
  checks.push("Authenticated inventory server pagination");
  await search(page);
  await page
    .getByRole("button", { name: "Orders Pentaho", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Pipeline operational details" })
    .waitFor();
  await screenshot(page, "pipeline-drawer");
  await page.keyboard.press("Tab");
  assert.equal(
    await page
      .getByRole("dialog")
      .evaluate((e) => e.contains(document.activeElement)),
    true,
  );
  await page.keyboard.press("Escape");
  await screenshot(page, "inventory");
  await route(page, "executions");
  const table = page.getByRole("region", {
    name: "Execution history",
    exact: true,
  });
  await table.getByRole("button", { name: f.retried, exact: true }).waitFor();
  assert.match(await table.textContent(), /SUCCESS AFTER RETRY/);
  assert.match(await table.textContent(), /WAITING FOR RETRY/);
  assert.match(await table.textContent(), /CONFLICTED EVIDENCE/);
  assert.match(await table.textContent(), /UNKNOWN/);
  await screenshot(page, "executions");
  const filteredExecutions = page.waitForResponse(
    (r) => r.url().includes("outcome=WAITING_FOR_RETRY") && r.status() === 200,
  );
  await page.getByLabel("Execution outcome").selectOption("WAITING_FOR_RETRY");
  await filteredExecutions;
  await table.getByRole("button").first().waitFor();
  assert.equal(await table.getByRole("button").count(), 1);
  await page.getByLabel("Execution outcome").selectOption("");
  await table.getByRole("button", { name: f.retried, exact: true }).click();
  await page
    .getByRole("navigation", { name: "Execution detail sections" })
    .getByRole("button", { name: "Attempts", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Execution attempts" })
    .getByRole("row")
    .nth(2)
    .waitFor();
  await screenshot(page, "execution-attempts");
  await close(page);
  checks.push(
    "Canonical outcomes, pending retry, attempt drawer, incomplete evidence and conflicts",
  );
  await route(page, "schedules");
  await page
    .getByText("Configured monitoring expectation", { exact: true })
    .first()
    .waitFor();
  const schedules = page.getByRole("region", { name: "Schedule occurrences" });
  assert.match(await schedules.textContent(), /INCOMPLETE/);
  assert.doesNotMatch(await schedules.textContent(), /NO RUN/);
  await screenshot(page, "schedules");
  await schedules.getByRole("button").first().click();
  await screenshot(page, "schedule-drawer");
  await close(page);
  checks.push("Evaluated incomplete coverage does not become NO_RUN");
  await route(page, "evidence");
  await page
    .getByRole("button", { name: "EXECUTION_OUTCOME", exact: true })
    .first()
    .click();
  await page
    .getByRole("heading", { name: "Previous defensible projection" })
    .waitFor();
  await screenshot(page, "review-drawer");
  const reviewPath =
    "/api/v1/unified/resources/" +
    f.resource +
    "/evidence-reviews/" +
    f.review +
    "/decision";
  await request(page, reviewPath, {
    action: "DEFER",
    expected_revision: 1,
    idempotency_key: "browser-concurrent",
    reason: "Controlled concurrent reviewer revision test",
  });
  const form = page.getByRole("form", { name: "Submit evidence decision" });
  await form
    .getByLabel("Decision reason")
    .fill("Stale controlled revision must not overwrite another reviewer");
  await form.getByRole("checkbox").check();
  await form
    .getByRole("button", { name: "Submit evidence decision", exact: true })
    .click();
  await form
    .getByRole("alert")
    .filter({ hasText: "This record changed" })
    .waitFor();
  assert.equal(
    await form
      .getByRole("button", { name: "Submit evidence decision", exact: true })
      .isDisabled(),
    true,
  );
  await form
    .getByRole("button", { name: "Refresh record before another decision" })
    .click();
  await page
    .getByRole("region", { name: "Review decisions" })
    .getByText("2 · DEFER", { exact: true })
    .waitFor();
  await decide(page, "Submit evidence decision");
  await page
    .getByRole("region", { name: "Review decisions" })
    .getByText("3 · DEFER", { exact: true })
    .waitFor();
  await close(page);
  await screenshot(page, "evidence");
  checks.push(
    "Actual stale revision 409, explicit confirmation and refreshed adjudication",
  );
  await recovery(page);
  await page
    .getByLabel("Separate successful execution")
    .selectOption(f.recovered);
  await page
    .getByRole("group", { name: "Original failure evidence" })
    .getByRole("checkbox")
    .first()
    .check();
  await page
    .getByRole("group", { name: "Separate recovery evidence" })
    .getByRole("checkbox")
    .first()
    .check();
  await decide(page, "Propose recovery association");
  await page
    .getByText(
      "Independent confirmation required. You cannot confirm your own proposal.",
      { exact: true },
    )
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", {
        name: "Confirm recovery association",
        exact: true,
      })
      .count(),
    0,
  );
  await screenshot(page, "recovery");
  checks.push(
    "Proposal references both accepted events; proposer cannot self-confirm",
  );
  const reviewer = await session(f.reviewer);
  await search(reviewer);
  await recovery(reviewer);
  await decide(reviewer, "Confirm recovery association");
  await reviewer
    .getByRole("button", { name: "Reverse recovery association", exact: true })
    .waitFor();
  await decide(reviewer, "Reverse recovery association");
  await reviewer.getByText("REVERSED", { exact: true }).waitFor();
  assert.match(
    await reviewer
      .getByRole("region", { name: "Recovery execution selection" })
      .getByRole("row")
      .filter({ hasText: f.original })
      .textContent(),
    /FAILED/,
  );
  await screenshot(reviewer, "recovery-reversed");
  await reviewer.close();
  checks.push(
    "Independent confirmation and reversal preserve original FAILED execution",
  );
  await route(page, "incidents");
  await page
    .getByRole("region", { name: "Native incident correlation" })
    .getByRole("row")
    .filter({ hasText: f.incident })
    .getByRole("button")
    .click();
  await page
    .getByRole("navigation", { name: "Incident detail sections" })
    .getByRole("button", { name: "Recovery", exact: true })
    .click();
  await page
    .getByText("Restoration is not verified.", { exact: false })
    .waitFor();
  await decide(page, "Record recovery assessment");
  await page
    .getByRole("navigation", { name: "Incident detail sections" })
    .getByRole("button", { name: "Recovery", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Recovery assessment history" })
    .getByRole("row")
    .nth(1)
    .waitFor();
  await screenshot(page, "incident-recovery");
  assert.equal(
    await page
      .getByRole("button", { name: "Validate recovery evidence", exact: true })
      .count(),
    0,
  );
  await close(page);
  await screenshot(page, "incidents");
  checks.push(
    "Assessment records failed validation without declaring restoration",
  );
  await route(page, "inventory");
  let release, seen;
  const delayed = new Promise((resolve) => {
      release = resolve;
    }),
    started = new Promise((resolve) => {
      seen = resolve;
    });
  let once = true;
  await page.route("**/api/v1/unified/resources?**", async (r) => {
    if (once && r.request().url().includes(f.organization)) {
      once = false;
      const response = await r.fetch();
      seen();
      await delayed;
      try {
        await r.fulfill({ response });
      } catch {}
    } else await r.continue();
  });
  await page
    .getByRole("button", { name: "Refresh evidence", exact: true })
    .click();
  await started;
  await switchCustomer(page, "Sprint 07 Alpha", "Sprint 07 Beta");
  release();
  await page.unroute("**/api/v1/unified/resources?**");
  await page
    .getByRole("button", { name: "Beta isolated pipeline", exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Orders Pentaho", exact: true })
      .count(),
    0,
  );
  checks.push(
    "Real customer selection clears sensitive data and discards delayed response",
  );
  await page.getByLabel("Global environment").selectOption("PROD");
  await page
    .getByText("No matching records in this authorized scope.", { exact: true })
    .waitFor();
  assert.equal(
    await page
      .getByRole("button", { name: "Beta isolated pipeline", exact: true })
      .count(),
    0,
  );
  await page.getByLabel("Global environment").selectOption("TEST");
  await page
    .getByRole("button", { name: "Beta isolated pipeline", exact: true })
    .waitFor();
  checks.push("Environment changes clear data and show the scoped empty state");
  await switchCustomer(page, "Sprint 07 Beta", "Sprint 07 Native");
  await route(page, "schedules");
  await page
    .getByText("Verified native scheduler", { exact: true })
    .first()
    .waitFor();
  checks.push(
    "Verified native scheduler and monitoring expectation labels remain distinct",
  );
  await switchCustomer(page, "Sprint 07 Native", "Sprint 07 Alpha");
  await route(page, "inventory");
  await page.getByLabel("Find pipeline", { exact: true }).fill("AIRFLOW");
  await page
    .getByRole("button", { name: "Search pipelines", exact: true })
    .click();
  await page
    .getByRole("button", { name: "AIRFLOW compatible 00", exact: true })
    .waitFor();
  assert.match(
    await page
      .getByRole("region", { name: "Pipeline inventory" })
      .textContent(),
    /DAG/,
  );
  checks.push("Existing non-Pentaho native classification remains compatible");
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await screenshot(page, "inventory-" + width);
    const overflow = await page.evaluate(() => ({
      width: innerWidth,
      scroll: document.documentElement.scrollWidth,
      boxes: [...document.querySelectorAll("body *")]
        .filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
        .slice(0, 15)
        .map((e) => [e.tagName, e.className]),
    }));
    assert.ok(overflow.scroll <= overflow.width, JSON.stringify(overflow));
    const region = page.getByRole("region", { name: "Pipeline inventory" });
    await region.focus();
    await page.keyboard.press("ArrowRight");
    assert.equal(
      await region.evaluate((e) => e.scrollWidth > e.clientWidth),
      true,
    );
  }
  checks.push(
    "Mobile/tablet tables scroll inside page and accept keyboard navigation",
  );
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Collapse sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Expand sidebar", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Data Sources / Resources", exact: true })
    .click();
  await page.getByRole("tab", { name: "Organizations", exact: true }).click();
  await page
    .getByRole("region", { name: "Monitored customer organizations" })
    .getByText("Sprint 07 Alpha", { exact: true })
    .waitFor();
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Employees", exact: true })
    .click();
  await page
    .getByRole("navigation", { name: "Access Management sections" })
    .waitFor();
  await page
    .getByRole("navigation", { name: "Access Management sections" })
    .getByRole("button", { name: "Departments", exact: true })
    .waitFor();
  checks.push("Collapsible shell and independent Resource/Access navigation");
  const viewer = await session(f.viewer);
  await search(viewer);
  await route(viewer, "evidence");
  await viewer
    .getByRole("button", { name: "EXECUTION_OUTCOME", exact: true })
    .first()
    .click();
  await viewer
    .getByText(
      "Adjudication requires etl.resolve_identity for this customer.",
      { exact: true },
    )
    .waitFor();
  assert.equal(
    await viewer
      .getByRole("button", { name: "Submit evidence decision", exact: true })
      .count(),
    0,
  );
  await request(
    viewer,
    reviewPath,
    {
      action: "DEFER",
      expected_revision: 3,
      idempotency_key: "unauthorized-browser",
      reason: "Controlled denied mutation",
    },
    403,
  );
  await close(viewer);
  await recovery(viewer);
  assert.equal(
    await viewer
      .getByRole("button", {
        name: "Propose recovery association",
        exact: true,
      })
      .count(),
    0,
  );
  await route(viewer, "executions");
  await viewer
    .getByRole("region", { name: "Execution history" })
    .getByRole("button", { name: f.original, exact: true })
    .waitFor();
  await viewer.route("**/api/v1/unified/resources/*/executions?**", (r) =>
    r.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Controlled unavailable transport" }),
    }),
  );
  await viewer
    .getByRole("button", { name: "Refresh evidence", exact: true })
    .click();
  await viewer
    .getByRole("alert")
    .filter({ hasText: "Last received data is stale" })
    .waitFor();
  assert.equal(
    await viewer
      .getByRole("region", { name: "Execution history" })
      .getByRole("button", { name: f.original, exact: true })
      .count(),
    1,
  );
  await viewer.unroute("**/api/v1/unified/resources/*/executions?**");
  checks.push(
    "Injected transport failure retains evidence with explicit stale/error state",
  );
  await viewer.close();
  checks.push(
    "Unauthorized adjudication/recovery controls hidden and API returns 403",
  );
  const restricted = await session(f.restricted);
  await restricted
    .getByText("Resource discovery requires resources.view", { exact: false })
    .waitFor();
  assert.equal(
    await restricted.getByLabel("Find pipeline", { exact: true }).count(),
    0,
  );
  await restricted.close();
  checks.push(
    "Catalog discovery honors resources.view without implicit permission grants",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    join(out, "sprint07-browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        browser: "Chromium",
        backend: "Actual authenticated API / owned PostgreSQL",
        fixtureAuthority: "CONTROLLED_FIXTURE",
        genuinePentahoRuntimeAcceptance: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "Sprint 07 actual browser acceptance PASS: " + checks.length + " groups",
  );
} catch (e) {
  if (inspected) {
    await screenshot(inspected, "failure");
    await writeFile(
      join(process.env.V16_PRIVATE_DIR, "sprint07-failure-dom.txt"),
      await inspected.locator("body").innerText(),
    );
  }
  throw e;
} finally {
  await browser.close();
}
