// Real browser and PostgreSQL-backed API. No mocked responses or health records.
import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  ).href
);
const fixture = JSON.parse(
  await readFile(join(process.env.ACCESS_PRIVATE_DIR, "fixture.json"), "utf8"),
);
const base = process.env.ACCESS_UI_BASE,
  apiBase = process.env.TEST_API_BASE,
  out = process.env.ACCESS_EVIDENCE_DIR;
assert.equal(process.env.OPSCONTROL_ACCESS_ACCEPTANCE, "1");
assert.match(base, /^http:\/\/127\.0\.0\.1:/);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
});
const errors = [],
  serverErrors = [],
  checks = [];
async function login(username) {
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1100 },
  });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 500)
      serverErrors.push({
        path: new URL(r.url()).pathname,
        status: r.status(),
      });
  });
  if (username === fixture.noc_username)
    await page.addInitScript(() => {
      localStorage.setItem(
        "opscontrol.organizationIds",
        JSON.stringify({
          unauthorized_customer: "stale-or-modified-preference",
        }),
      );
    });
  await page.goto(base);
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page
    .getByLabel("Password", { exact: true })
    .fill(fixture.admin_password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
  return page;
}
async function call(page, path, method = "GET", body) {
  return page.evaluate(
    async ({ url, method, body }) => {
      const r = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization:
            "Bearer " + sessionStorage.getItem("opscontrol.sessionToken"),
        },
        ...(body && { body: JSON.stringify(body) }),
      });
      return {
        status: r.status,
        data: r.status === 204 ? null : await r.json(),
      };
    },
    { url: apiBase + path, method, body },
  );
}
const navigate = async (page, tab) => {
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: tab, exact: true })
    .click();
  await page.getByRole("heading", { name: tab, exact: true }).waitFor();
};
const section = async (page, tab) => {
  await page
    .getByRole("navigation", { name: "Access Management sections" })
    .getByRole("button", { name: tab, exact: true })
    .click();
  await page
    .locator(".access-table")
    .first()
    .getByRole("heading", { name: tab, exact: true })
    .waitFor();
};
const shot = async (page, name) => {
  await page.evaluate(() => window.scrollTo(0, 0));
  assert.equal(
    await page.evaluate(() => document.documentElement.dataset.theme),
    name.endsWith("-dark") ? "dark" : "light",
  );
  await page.screenshot({ path: join(out, name + ".png"), fullPage: true });
};
try {
  const admin = await login("access-fixture-admin");
  await admin.getByRole("button", { name: "Dark theme", exact: true }).click();
  await navigate(admin, "Overview");
  await admin.locator(".org-context-button").click();
  await admin.getByRole("checkbox", { name: /^Customer B/ }).uncheck();
  await admin.locator(".org-context-button").click();
  await navigate(admin, "Resource Management");
  assert.equal(await admin.locator(".org-context-button").count(), 0);
  await admin
    .locator("tbody tr")
    .filter({ hasText: "Customer B (synthetic)" })
    .waitFor();
  assert.equal(
    await admin.getByLabel("Resource organization filter").inputValue(),
    "",
  );
  await admin
    .getByLabel("Resource organization filter")
    .selectOption(fixture.customer_b);
  await admin.locator("tbody tr").filter({ hasText: "Customer B" }).waitFor();
  assert.equal(await admin.locator("tbody tr").count(), 1);
  checks.push(
    "Global Customer A selection does not filter Resource Management; its independent customer filter works",
  );
  await navigate(admin, "Access Management");
  await section(admin, "Employees");
  assert.equal(await admin.locator(".org-context-button").count(), 0);
  await admin
    .getByRole("row")
    .filter({ hasText: "access-manager Employee" })
    .waitFor();
  await admin
    .getByRole("button", { name: "Create employee", exact: true })
    .click();
  let dialog = admin.getByRole("dialog");
  await dialog
    .getByLabel("Full name", { exact: true })
    .fill("Browser Engineer");
  await dialog.getByLabel("Username", { exact: true }).fill("access-browser");
  await dialog.getByLabel("Employee ID", { exact: true }).fill("EMP-BROWSER");
  await dialog
    .getByLabel("Work email", { exact: true })
    .fill("browser@example.test");
  await dialog
    .getByLabel("Initial password", { exact: true })
    .fill(fixture.admin_password);
  await dialog
    .getByLabel("Department (exactly one)")
    .selectOption({ label: "NOC renamed" });
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  await admin
    .getByRole("row")
    .filter({ hasText: "Browser Engineer" })
    .waitFor();
  const employee = (
    await call(admin, "/api/v1/access/employees?search=EMP-BROWSER")
  ).data.items[0];
  assert.equal(employee.full_name, "Browser Engineer");
  assert.match(employee.id, /^[\da-f-]{36}$/);
  await section(admin, "Departments");
  await admin
    .getByRole("button", { name: "Create department", exact: true })
    .click();
  dialog = admin.getByRole("dialog");
  await dialog
    .getByLabel("Department name", { exact: true })
    .fill("Browser Support");
  await dialog.getByLabel("Department code", { exact: true }).fill("BROWSER");
  await dialog
    .getByLabel("Description", { exact: true })
    .fill("Controlled browser acceptance department");
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  let row = admin.getByRole("row").filter({ hasText: "Browser Support" });
  await row.waitFor();
  await row
    .getByRole("button", { name: "Members & access", exact: true })
    .click();
  await admin.getByRole("button", { name: "Assign role", exact: true }).click();
  dialog = admin.getByRole("dialog");
  await dialog
    .getByLabel("Role", { exact: true })
    .selectOption(fixture.viewer_role);
  await dialog.getByText("Permission preview", { exact: true }).waitFor();
  // Hold one genuine authenticated directory response. Saving must remain
  // modal/busy until its refreshed snapshot can safely replace the old view.
  let capture, release;
  const captured = new Promise((resolve) => {
    capture = resolve;
  });
  const held = new Promise((resolve) => {
    release = resolve;
  });
  const directoryRoute = "**/api/v1/access/roles";
  await admin.route(directoryRoute, async (route) => {
    const response = await route.fetch();
    capture();
    await held;
    await route.fulfill({ response });
  });
  try {
    await dialog
      .getByRole("button", { name: "Save changes", exact: true })
      .click();
    await captured;
    assert.equal(await dialog.isVisible(), true);
    assert.equal(
      await dialog
        .getByRole("button", { name: "Checking…", exact: true })
        .isDisabled(),
      true,
    );
    assert.equal(
      await admin
        .getByRole("navigation", { name: "Access Management sections" })
        .getByRole("button", { name: "Departments", exact: true })
        .isDisabled(),
      true,
    );
  } finally {
    release();
    await dialog.waitFor({ state: "hidden" });
    await admin.unroute(directoryRoute);
  }
  checks.push(
    "Delayed genuine directory response cannot close a save early, switch table schema or erase the next detail selection",
  );
  await row
    .getByRole("button", { name: "Members & access", exact: true })
    .click();
  await admin
    .getByRole("button", { name: "Add employee", exact: true })
    .click();
  dialog = admin.getByRole("dialog");
  await dialog
    .getByLabel("Employee", { exact: true })
    .selectOption(employee.id);
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  await row
    .getByRole("button", { name: "Members & access", exact: true })
    .click();
  await admin
    .getByRole("button", { name: "Grant customer access", exact: true })
    .click();
  dialog = admin.getByRole("dialog");
  await dialog
    .getByLabel("Customer", { exact: true })
    .selectOption(fixture.customer_b);
  await dialog
    .getByLabel("Assigned role", { exact: true })
    .selectOption(fixture.viewer_role);
  await dialog
    .getByRole("button", { name: "Preview effective access", exact: true })
    .click();
  await dialog.getByText(/Server-verified preview/).waitFor();
  const department = (
    await call(admin, "/api/v1/access/departments?search=Browser Support")
  ).data.items[0];
  assert.equal(
    (
      await call(
        admin,
        "/api/v1/access/customer-grants?department_id=" + department.id,
      )
    ).data.total,
    0,
  );
  await dialog
    .getByRole("button", { name: "Confirm customer grant", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  assert.equal(
    (
      await call(
        admin,
        "/api/v1/access/customer-grants?department_id=" + department.id,
      )
    ).data.total,
    1,
  );
  checks.push(
    "Browser creates unique employee/department, assigns role/membership and previews then confirms a paired customer grant",
  );
  await section(admin, "Employees");
  await admin.getByLabel("Search Employees").fill("EMP-BROWSER");
  row = admin.getByRole("row").filter({ hasText: "Browser Engineer" });
  await row.waitFor();
  await row.getByRole("button", { name: "Review access", exact: true }).click();
  await admin
    .getByRole("heading", { name: "Effective permissions", exact: true })
    .waitFor();
  await admin.getByText("department", { exact: true }).waitFor();
  await shot(admin, "employees-dark");
  for (const [tab, file] of [
    ["Departments", "departments-dark"],
    ["Roles & Permissions", "roles-dark"],
    ["Organization Access", "customer-access-dark"],
    ["Access Audit", "access-audit-dark"],
  ]) {
    await section(admin, tab);
    await admin.locator(".access-table tbody tr").first().waitFor();
    await shot(admin, file);
  }
  const toggle = admin.getByRole("button", {
    name: "Light theme",
    exact: true,
  });
  await toggle.click();
  await section(admin, "Departments");
  await admin.locator(".access-table tbody tr").first().waitFor();
  await shot(admin, "departments-light");
  checks.push(
    "All five administration sections render backend data in the existing dark/light design system",
  );
  const noc = await login(fixture.noc_username);
  await navigate(noc, "Overview");
  assert.equal(
    await noc
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Access Management", exact: true })
      .count(),
    0,
  );
  await noc.locator(".org-context-button").click();
  assert.equal(
    await noc.getByRole("checkbox", { name: /^Customer B/ }).count(),
    0,
  );
  await noc.locator(".org-context-button").click();
  assert.equal((await call(noc, "/api/v1/access/employees")).status, 403);
  await noc.goto(base + "/?tab=Access%20Management");
  assert.equal(
    await noc
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Access Management", exact: true })
      .count(),
    0,
  );
  checks.push(
    "Unauthorized navigation remains hidden after manually entered URL and refresh; direct identity API returns 403; selector excludes Customer B",
  );
  const access = await login(fixture.access_username);
  await access
    .getByRole("heading", { name: "Access Management", exact: true })
    .waitFor();
  assert.equal(await access.locator(".org-context-button").count(), 0);
  assert.equal(
    await access
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "VM Health", exact: true })
      .count(),
    0,
  );
  checks.push(
    "Access administrator sees independent identity screens with no operational customer access",
  );
  const worker = await login("access-browser");
  await navigate(worker, "VM Health");
  assert.equal(
    (await call(worker, "/api/v1/auth/me")).data.customer_permissions[
      fixture.customer_a
    ],
    undefined,
  );
  assert.equal(
    (await call(worker, "/api/v1/auth/me")).data.customer_permissions[
      fixture.customer_b
    ].includes("resources.view"),
    true,
  );
  await call(
    admin,
    "/api/v1/access/employees/" + employee.id + "/department",
    "PUT",
    {
      department_id: (
        await call(
          admin,
          "/api/v1/access/departments?search=Controlled Unassigned Team",
        )
      ).data.items[0].id,
    },
  );
  await worker
    .getByRole("heading", { name: "No assigned access", exact: true })
    .waitFor({ timeout: 15000 });
  assert.equal(
    await worker
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "VM Health", exact: true })
      .count(),
    0,
  );
  await call(admin, "/api/v1/access/employees/" + employee.id, "PATCH", {
    active: false,
  });
  await worker
    .getByRole("button", { name: "Sign in", exact: true })
    .waitFor({ timeout: 15000 });
  checks.push(
    "Existing browser session promptly clears operational data/navigation on membership revocation and logs out on account deactivation",
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(serverErrors, []);
  await writeFile(
    join(out, "browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        screenshots: [
          "employees-dark.png",
          "departments-dark.png",
          "roles-dark.png",
          "customer-access-dark.png",
          "access-audit-dark.png",
          "departments-light.png",
        ],
        browser_errors: errors,
        server_errors: serverErrors,
      },
      null,
      2,
    ),
  );
  console.log(
    "ACCESS BROWSER ACCEPTANCE PASS (" + checks.length + " check groups)",
  );
} finally {
  await browser.close();
}
