import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE);
const fixture = JSON.parse(
  await readFile(join(process.env.ARCH001_PRIVATE_DIR, "fixture.json"), "utf8"),
);
const out = process.env.ARCH001_EVIDENCE_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const errors = [],
  failed = [];
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(e.message));
page.on("response", (r) => {
  if (r.url().includes("/api/v1/unified/") && r.status() >= 500)
    failed.push(r.status() + ":" + new URL(r.url()).pathname);
});
const nav = async (name) => {
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name, exact: true })
    .click();
};
const login = async (name) => {
  await page.goto(process.env.ARCH001_UI_URL);
  await page.getByLabel("Username", { exact: true }).fill(name);
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
};
try {
  await login("arch001-admin");
  assert.equal(
    await page.getByRole("button", { name: "Incidents", exact: true }).count(),
    0,
  );
  await page
    .getByLabel("Global environment", { exact: true })
    .selectOption("QA");
  await nav("Resource Management");
  assert.equal(
    await page.getByLabel("Global environment", { exact: true }).count(),
    0,
  );
  assert.equal(await page.locator(".org-context-button").count(), 0);
  await page
    .getByRole("heading", { name: "VM Resources", exact: true })
    .waitFor();
  await page
    .getByRole("cell", { name: fixture.vm_resource.name, exact: true })
    .waitFor()
    .catch(async () => {
      await page
        .getByRole("button", { name: fixture.vm_resource.name, exact: true })
        .waitFor();
    });
  assert.equal(
    await page.getByLabel("Resource environment filter").inputValue(),
    "",
  );
  await page.screenshot({
    path: join(out, "arch001-vm-resources.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Create VM Resource", exact: true })
    .click();
  await page.getByRole("dialog").waitFor();
  await page.screenshot({
    path: join(out, "arch001-vm-onboarding.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Close resource form" }).click();
  await page
    .getByRole("tab", { name: "Event Parameters", exact: true })
    .click();
  const domains = page.getByRole("tablist", {
    name: "Event Parameter domains",
  });
  assert.equal(await domains.getByRole("tab").count(), 3);
  for (const name of [
    "ETL Parameters",
    "VM Health Parameters",
    "API Parameters",
  ]) {
    await domains.getByRole("tab", { name, exact: true }).click();
    await page.getByRole("heading", { name, exact: true }).waitFor();
  }
  await page.screenshot({
    path: join(out, "arch001-api-parameters.png"),
    fullPage: true,
  });
  for (const name of [
    "Overview",
    "ETL Monitoring",
    "VM Health",
    "API Monitoring",
    "Alerts",
    "Reports",
  ]) {
    await nav(name);
    await page.getByRole("heading", { name, exact: true }).waitFor();
    await page.waitForTimeout(250);
  }
  for (const name of ["ETL Reports", "VM Health Reports", "API Reports"]) {
    await page.getByRole("tab", { name, exact: true }).click();
    await page.waitForTimeout(500);
  }
  await page.screenshot({
    path: join(out, "arch001-api-reports.png"),
    fullPage: true,
  });
  await nav("Access Management");
  assert.equal(
    await page.getByLabel("Global environment", { exact: true }).count(),
    0,
  );
  assert.equal(
    await page
      .getByRole("button", { name: "Organization Access", exact: true })
      .count(),
    0,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await nav("Resource Management");
  await page.screenshot({
    path: join(out, "arch001-mobile-resources.png"),
    fullPage: true,
  });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2,
    ),
    false,
    "Page must not overflow viewport",
  );
  assert.deepEqual(errors, []);
  assert.deepEqual(failed, []);
  await context.close();
  const restricted = await browser.newContext();
  const reader = await restricted.newPage();
  await reader.goto(process.env.ARCH001_UI_URL);
  await reader.getByLabel("Username", { exact: true }).fill("arch001-reader");
  await reader.getByLabel("Password", { exact: true }).fill(fixture.password);
  await reader.getByRole("button", { name: "Sign in", exact: true }).click();
  await reader
    .getByRole("navigation", { name: "Primary navigation" })
    .waitFor();
  assert.equal(
    await reader
      .getByRole("button", { name: "Access Management", exact: true })
      .count(),
    0,
  );
  await restricted.close();
  await writeFile(
    join(out, "browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        origin: "ACTUAL_PLAYWRIGHT_AND_OWNED_FASTAPI",
        screenshots: 5,
        incident_ui: false,
        customer_grants_ui: false,
        rbac: true,
        resource_selector_independent: true,
      },
      null,
      2,
    ),
  );
  console.log(
    "ARCH-001 actual browser navigation, domain tables, independent admin filters, reports, mobile and access negatives PASS",
  );
} finally {
  await browser.close();
}
