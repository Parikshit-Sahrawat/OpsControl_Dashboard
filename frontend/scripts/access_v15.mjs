import { scopeHeaders } from "./explicit_scope.mjs";
// PostgreSQL-backed browser checks. This script only runs in the owned ARCH lab.
import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  ).href
);
const fixture = JSON.parse(
  await readFile(join(process.env.ARCH001_PRIVATE_DIR, "fixture.json"), "utf8"),
);
const base = process.env.ARCH001_UI_URL,
  apiBase = process.env.ARCH001_API_URL;
assert.match(base, /^https?:\/\/(127\.0\.0\.1|localhost):/);
const out = process.env.ARCH001_EVIDENCE_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const errors = [],
  checks = [];
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
page.on("pageerror", (error) => errors.push(error.message));
page.on("dialog", (dialog) => dialog.accept());
const call = async (path) => {
  const scope = await scopeHeaders(
    page.request,
    apiBase,
    await page.evaluate(() =>
      sessionStorage.getItem("opscontrol.sessionToken"),
    ),
  );
  return page.evaluate(
    async ({ url, scope }) => {
      const response = await fetch(url, {
        headers: {
          ...scope,
          Authorization:
            "Bearer " + sessionStorage.getItem("opscontrol.sessionToken"),
        },
      });
      return { status: response.status, body: await response.json() };
    },
    { url: apiBase + path, scope },
  );
};
async function login(name) {
  await page.goto(base);
  await page.getByLabel("Username", { exact: true }).fill(name);
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
}
const section = async (name) => {
  await page
    .getByRole("navigation", { name: "Access Management sections" })
    .getByRole("button", { name, exact: true })
    .click();
  await page
    .locator(".access-table")
    .first()
    .getByRole("heading", { name, exact: true })
    .waitFor();
};
try {
  await login("arch001-admin");
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Access Management", exact: true })
    .click();
  assert.equal(
    await page.getByLabel("Global environment", { exact: true }).count(),
    0,
  );
  assert.equal(await page.locator(".org-context-button").count(), 0);
  const suffix = Date.now().toString(36),
    departmentName = "UAT Internal " + suffix,
    employeeName = "UAT Operator " + suffix,
    username = "uat-operator-" + suffix;
  await page
    .getByRole("button", { name: "Create Department", exact: true })
    .click();
  let dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Department name", { exact: true })
    .fill(departmentName);
  await dialog
    .getByLabel("Department code", { exact: true })
    .fill("UAT-" + suffix);
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  await page
    .getByRole("button", { name: "Create Employee", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog.getByLabel("Full name", { exact: true }).fill(employeeName);
  await dialog.getByLabel("Username", { exact: true }).fill(username);
  await dialog
    .getByLabel("Work email", { exact: true })
    .fill(username + "@example.test");
  await dialog
    .getByLabel("Department (exactly one)", { exact: true })
    .selectOption({ label: departmentName });
  await dialog
    .getByLabel("Initial password", { exact: true })
    .fill(fixture.password);
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await dialog.waitFor({ state: "hidden" });
  await section("Employees");
  for (const name of ["Name", "Username", "Email"])
    await page.getByRole("columnheader", { name, exact: true }).waitFor();
  await page.getByLabel("Search Employees", { exact: true }).fill(username);
  const row = page.locator("tbody tr").filter({ hasText: username });
  await row.getByRole("cell", { name: employeeName, exact: true }).waitFor();
  await row
    .getByRole("cell", { name: username + "@example.test", exact: true })
    .waitFor();
  const employeeResult = await call(
    "/api/v1/access/employees?search=" + encodeURIComponent(username),
  );
  assert.equal(employeeResult.status, 200);
  assert.equal(employeeResult.body.items.length, 1);
  const employee = employeeResult.body.items[0];
  assert.equal(employee.departments.filter((d) => d.active).length, 1);
  assert.equal(employee.password_hash, undefined);
  assert.equal(employee.password, undefined);
  checks.push(
    "Manual employee creation requires one existing internal department; distinct identity columns render actual values and no password is returned.",
  );
  await section("Departments");
  await page
    .getByLabel("Search Departments", { exact: true })
    .fill(departmentName);
  await page
    .locator("tbody tr")
    .filter({ hasText: departmentName })
    .getByRole("button", { name: "Members & access", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: employeeName + " · Review effective permissions",
      exact: true,
    })
    .waitFor();
  await page
    .getByRole("button", {
      name: employeeName + " · Review effective permissions",
      exact: true,
    })
    .click();
  await page
    .getByRole("heading", { name: "Effective permissions", exact: true })
    .waitFor();
  assert.notEqual(employee.id, employee.departments[0].id);
  const effective = await call(
    "/api/v1/access/employees/" + employee.id + "/effective-permissions",
  );
  assert.equal(effective.status, 200);
  assert.deepEqual(effective.body.customer_permissions, {});
  checks.push(
    "Department Members & Access reaches member effective permissions; department and user UUIDs differ and creation grants no implicit customer access.",
  );
  await page
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Guided Department → Employee → Permissions",
      exact: true,
    })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "3. Permissions", exact: true })
    .click();
  await dialog
    .locator('input[placeholder="Name, username or employee ID"]')
    .fill(username);
  await dialog
    .getByLabel("Employee", { exact: true })
    .selectOption(employee.id);
  await dialog
    .getByRole("heading", { name: "Existing organization scopes", exact: true })
    .waitFor();
  const rolesResponse = await call("/api/v1/access/roles");
  assert.equal(rolesResponse.status, 200);
  const viewerRole = rolesResponse.body.find(
    (role) => role.active && role.code === "read-only-viewer",
  );
  assert.ok(viewerRole, "Reviewed read-only role exists");
  await dialog
    .getByLabel("Role / configured permissions", { exact: true })
    .selectOption(viewerRole.id);
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().endsWith("/effective-permissions") &&
        response.status() === 200,
    ),
    dialog.getByRole("button", { name: "Assign Role", exact: true }).click(),
  ]);
  const assigned = await call(
    "/api/v1/access/employees/" + employee.id + "/effective-permissions",
  );
  assert.equal(assigned.status, 200);
  assert.ok(
    assigned.body.inherited_and_direct.some(
      (source) => source.role === viewerRole.name,
    ),
  );
  assert.deepEqual(assigned.body.customer_permissions, {});

  await page.screenshot({
    path: join(out, "access-v15-permissions.png"),
    fullPage: true,
  });
  await dialog
    .getByRole("button", { name: "Close onboarding", exact: true })
    .click();
  checks.push(
    "Permissions onboarding searches existing employees and displays inherited/direct permissions and existing scoped access without organization management.",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await section("Employees");
  await page.getByLabel("Search Employees", { exact: true }).fill(username);
  await page.locator("tbody tr").filter({ hasText: username }).waitFor();
  assert.ok(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth + 1,
    ),
  );
  await page.screenshot({
    path: join(out, "access-v15-mobile.png"),
    fullPage: true,
  });
  checks.push(
    "Employee table scrolls within its card at mobile width without document overflow.",
  );
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login("arch001-reader");
  assert.equal(
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("button", { name: "Access Management", exact: true })
      .count(),
    0,
  );
  assert.equal((await call("/api/v1/access/employees")).status, 403);
  checks.push(
    "Unauthorized user has no Access Management navigation and direct employee API returns 403.",
  );
  assert.deepEqual(errors, []);
  await writeFile(
    join(out, "access-v15-browser.json"),
    JSON.stringify({ status: "PASS", checks }, null, 2) + "\n",
  );
  console.log("PASS: " + checks.length + " access V1.5 browser checks");
} catch (error) {
  console.log(
    "Access browser diagnostics:",
    JSON.stringify({
      headings: await page.getByRole("heading").allTextContents(),
      headers: await page.getByRole("columnheader").allTextContents(),
      alerts: await page.getByRole("alert").allTextContents(),
      loading: await page.getByRole("status").allTextContents(),
      errors,
      employees: (await call("/api/v1/access/employees")).status,
      table: await page
        .locator("table")
        .first()
        .evaluate((table) => ({
          role: table.getAttribute("role"),
          display: getComputedStyle(table).display,
          headers: Array.from(table.querySelectorAll("th")).map((th) => ({
            text: th.textContent,
            role: th.getAttribute("role"),
            scope: th.scope,
            display: getComputedStyle(th).display,
            hidden: th.getAttribute("aria-hidden"),
          })),
        }))
        .catch(() => null),
    }),
  );
  await page.screenshot({
    path: join(out, "access-v15-failure.png"),
    fullPage: true,
  });
  throw error;
} finally {
  await browser.close();
}
