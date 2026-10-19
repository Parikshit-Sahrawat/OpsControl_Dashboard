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
    join(process.env.V16_PRIVATE_DIR, "sprint08-fixture.json"),
    "utf8",
  ),
);
const adminFixture = JSON.parse(
  await readFile(join(process.env.V16_PRIVATE_DIR, "api-fixture.json"), "utf8"),
);
const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
  }),
  checks = [],
  errors = [];
let inspected;
async function login(name) {
  const p = await browser.newPage({ viewport: { width: 1400, height: 950 } });
  inspected = p;
  p.setDefaultTimeout(20000);
  p.on("pageerror", (e) => errors.push(e.message));
  await p.addInitScript(
    (id) =>
      localStorage.setItem("opscontrol.organizationIds", JSON.stringify([id])),
    f.organization,
  );
  await p.goto(process.env.V16_UI_URL + "/#/pipelines/inventory");
  await p.getByLabel("Username", { exact: true }).fill(name);
  await p.getByLabel("Password", { exact: true }).fill(f.password);
  await p.getByRole("button", { name: "Sign in", exact: true }).click();
  await p.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  return p;
}
async function shot(p, name) {
  await p.screenshot({
    path: join(process.env.V16_EVIDENCE_DIR, "sprint08-" + name + ".png"),
    fullPage: true,
  });
}
try {
  const editor = await login(f.operator);
  await editor
    .getByRole("button", { name: "Sprint 08 secured Pentaho", exact: true })
    .waitFor();
  await editor.locator(".org-context-button").click();
  await editor.getByRole("checkbox", { name: /ALL customers/ }).waitFor();
  await editor.getByRole("checkbox", { name: /ALL customers/ }).check();
  await editor.locator(".org-context-button").click();
  await editor
    .getByRole("heading", { name: "Pipeline Inventory", exact: true })
    .waitFor();
  await shot(editor, "all-scope");
  checks.push(
    "Explicit ALL appears only with elevated authority and is a separate selection",
  );
  // Return to one explicit customer through the real selector, then open a drawer.
  await editor.locator(".org-context-button").click();
  await editor.getByRole("checkbox", { name: /ALL customers/ }).uncheck();
  await editor
    .getByRole("checkbox", { name: /Sprint 08 scoped customer/ })
    .check();
  await editor.locator(".org-context-button").click();
  await editor
    .getByRole("button", { name: "Sprint 08 secured Pentaho", exact: true })
    .click();
  await editor.getByRole("dialog").waitFor();
  const response = await editor.request.post(
    process.env.V16_API_URL + "/api/v1/auth/login",
    { data: { username: "v16-api-admin", password: adminFixture.password } },
  );
  assert.ok(response.ok());
  const token = (await response.json()).access_token;
  const me = await editor.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const profile = await editor.request.get(
    process.env.V16_API_URL + "/api/v1/auth/me",
    { headers: { Authorization: "Bearer " + me } },
  );
  const user = (await profile.json()).id;
  const denied = await editor.request.post(
    process.env.V16_API_URL + "/api/v1/access/boundaries",
    {
      headers: { Authorization: "Bearer " + token },
      data: {
        user_id: user,
        kind: "DENY",
        specification: {
          permissions: ["etl.view", "resources.view"],
          customers: [f.organization],
        },
        active: true,
        idempotency_key: "s08-browser-revocation",
        reason: "Controlled browser revocation of active sensitive scope",
      },
    },
  );
  assert.ok(denied.ok(), await denied.text());
  await editor.getByRole("dialog").waitFor({ state: "hidden", timeout: 15000 });
  await editor
    .getByText("No matching records in this authorized scope.", { exact: true })
    .waitFor();
  await shot(editor, "revoked-drawer");
  checks.push(
    "Live authorization revision clears an open sensitive drawer and cached inventory",
  );
  const delegate = await login(f.delegate);
  await delegate.locator(".org-context-button").click();
  assert.equal(
    await delegate.getByRole("checkbox", { name: /ALL customers/ }).count(),
    0,
  );
  await delegate
    .getByRole("checkbox", { name: /Sprint 08 scoped customer/ })
    .uncheck();
  await delegate.locator(".org-context-button").click();
  await delegate
    .getByText("Select a customer with etl.view permission.", { exact: false })
    .waitFor();
  checks.push(
    "Non-elevated selector exposes no ALL and clearing the final customer removes operational data",
  );
  await delegate
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Access Management", exact: true })
    .click();
  await delegate
    .getByRole("navigation", { name: "Access Management sections" })
    .waitFor();
  await delegate
    .getByText(
      "Scope restrictions, delegated administration and ALL-customer authority",
      { exact: true },
    )
    .click();
  await delegate
    .getByRole("region", { name: "Access boundaries" })
    .getByRole("cell")
    .filter({ hasText: "DELEGATE" })
    .first()
    .waitFor();
  assert.equal(
    await delegate
      .getByRole("button", {
        name: "Save explicit access boundary",
        exact: true,
      })
      .count(),
    0,
  );
  await shot(delegate, "delegated-access");
  checks.push(
    "Delegation is explainable and platform-controlled policy mutations are unavailable to an ordinary administrator",
  );
  await delegate
    .getByRole("button", { name: "Create employee", exact: true })
    .click();
  const dept = delegate.getByLabel("Department (exactly one)", { exact: true });
  await dept.waitFor();
  assert.equal(await dept.getAttribute("multiple"), null);
  assert.equal(await dept.getAttribute("required"), "");
  await delegate.getByRole("button", { name: "Close access dialog" }).click();
  await delegate.setViewportSize({ width: 390, height: 900 });
  await shot(delegate, "access-mobile");
  assert.equal(
    await delegate.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    true,
  );
  checks.push(
    "Existing employee form requires exactly one department and Access Management remains responsive",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    join(process.env.V16_EVIDENCE_DIR, "sprint08-browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        backend: "Actual authenticated local API and owned PostgreSQL",
        genuine_runtime_acceptance: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "Sprint 08 actual Chromium authorization PASS: " +
      checks.length +
      " groups",
  );
} catch (e) {
  if (inspected && !inspected.isClosed()) {
    await shot(inspected, "failure");
    await writeFile(
      join(process.env.V16_PRIVATE_DIR, "sprint08-failure.txt"),
      await inspected.locator("body").innerText(),
    );
  }
  throw e;
} finally {
  await browser.close();
}
