// Actual authenticated browser and API evidence; no interception or fabricated telemetry.
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
  failed = [],
  screenshots = [];
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
page.on("pageerror", (e) => errors.push(e.message));
page.on("response", (r) => {
  if (r.url().includes("/api/v1/") && r.status() >= 500)
    failed.push(r.status() + ":" + new URL(r.url()).pathname);
});
const nav = async (name) =>
  page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name, exact: true })
    .click();
const shot = async (name) => {
  await page.screenshot({ path: join(out, name), fullPage: true });
  screenshots.push(name);
};
const response = (path, method = "GET") =>
  page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === path && r.request().method() === method,
  );
const close = () =>
  page.getByRole("button", { name: "Close resource form" }).click();
try {
  await page.goto(process.env.ARCH001_UI_URL);
  await page.getByLabel("Username", { exact: true }).fill("arch001-admin");
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  assert.equal(
    await page.getByRole("button", { name: "Incidents", exact: true }).count(),
    1,
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
    .getByRole("heading", { name: "Compute Instances", exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: fixture.vm_resource.name, exact: true })
    .waitFor();
  assert.equal(
    await page.getByLabel("Resource environment filter").inputValue(),
    "",
  );
  await shot("arch001-compute-resources.png");

  // Registry attributes and drafts are fetched from the real backend.
  const registryResponse = response("/api/v1/attribute-registry");
  await page
    .getByRole("button", { name: "Create Compute Instance", exact: true })
    .click();
  const registry = await (await registryResponse).json();
  assert(registry.version >= 1);
  assert(registry.definitions.VM.fields.some((f) => f.key === "environment"));
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/^Environment/).selectOption("DEV");
  const steps = dialog.getByRole("list", { name: "VM onboarding steps" });
  assert.equal(await steps.getByRole("button").count(), 10);
  const name = "Browser Compute " + Date.now();
  await dialog.getByLabel("Resource name", { exact: true }).fill(name);
  await dialog
    .getByLabel("Customer", { exact: true })
    .selectOption(fixture.vm_resource.organization_id);
  await dialog
    .getByLabel("Hostname", { exact: true })
    .fill("browser-compute.example.test");
  await dialog
    .getByLabel("DNS / IP address", { exact: true })
    .fill("203.0.113.71");
  await dialog.getByLabel("OS", { exact: true }).selectOption("Linux");
  const createResponse = response("/api/v1/unified/resources/vm", "POST");
  await dialog
    .getByRole("button", { name: "Save resource identity", exact: true })
    .click();
  const createdResponse = await createResponse;
  assert.equal(createdResponse.status(), 201);
  const created = await createdResponse.json();
  for (let stage = 2; stage <= 10; stage++) {
    await steps
      .getByRole("button")
      .nth(stage - 1)
      .click();
    assert.equal(
      await steps
        .getByRole("button")
        .nth(stage - 1)
        .getAttribute("aria-current"),
      "step",
    );
  }
  await steps.getByRole("button").nth(5).click();
  const draftResponse = response("/api/v1/resource-drafts", "POST");
  await dialog.getByRole("button", { name: "Save draft", exact: true }).click();
  const saved = await draftResponse;
  assert.equal(saved.status(), 201);
  const draft = await saved.json();
  assert.equal(draft.stage, 6);
  assert.equal(draft.configuration.resource_id, created.id);
  await shot("arch001-compute-onboarding.png");
  await close();
  await page
    .getByRole("button", { name: "Create Compute Instance", exact: true })
    .click();
  await dialog.getByLabel("Resume draft").selectOption(draft.id);
  await dialog
    .getByRole("heading", { name: "Event Parameters (optional)", exact: true })
    .waitFor();
  await steps.getByRole("button").nth(9).click();
  await dialog.getByLabel("Approve verified monitoring activation").check();
  const activationResponse = response(
    "/api/v1/unified/resources/" + created.id + "/activate",
    "POST",
  );
  await dialog
    .getByRole("button", { name: "Activate monitoring", exact: true })
    .click();
  const activation = await activationResponse;
  assert.equal(
    activation.status(),
    409,
    "An unregistered/no-telemetry host must not activate, even when optional stages are skipped",
  );
  assert.equal(
    (await activation.json()).detail.message,
    "Required telemetry verification has not passed",
    "Skipping optional stages must reach genuine telemetry readiness checks",
  );
  await dialog.getByRole("alert").waitFor();
  await close();

  for (const [area, listName, names] of [
    [
      "Event Parameters",
      "Event Parameter domains",
      [
        "Compute Health Parameters",
        "Data Pipeline Parameters",
        "API Endpoint Parameters",
      ],
    ],
    [
      "Alert Rules",
      "Event Parameter domains",
      [
        "Compute Instances Alert Setup",
        "Data Pipelines Alert Setup",
        "API Endpoints Alert Setup",
      ],
    ],
  ]) {
    await page.getByRole("tab", { name: area, exact: true }).click();
    const domains = page.getByRole("tablist", { name: listName });
    assert.equal(await domains.getByRole("tab").count(), 3);
    for (const domainName of names)
      await domains.getByRole("tab", { name: domainName, exact: true }).click();
  }
  await page
    .getByRole("tab", { name: "Notification Delivery", exact: true })
    .click();
  await page
    .getByRole("heading", { name: "Notification Delivery", exact: true })
    .waitFor();
  await page
    .getByLabel("Organization", { exact: true })
    .selectOption(fixture.vm_resource.organization_id);
  await page
    .getByRole("button", { name: "Create Destination", exact: true })
    .click();
  const destinationName = "Browser In-app " + Date.now();
  await page.getByLabel("Name", { exact: true }).fill(destinationName);
  await page.getByLabel("Channel", { exact: true }).selectOption("IN_APP");
  const destinationResponse = response("/api/v1/notification-delivery", "POST");
  await page.locator("form").getByRole("button", { name: /Save/ }).click();
  assert.equal((await destinationResponse).status(), 201);
  await page.getByRole("row").filter({ hasText: destinationName }).waitFor();
  await shot("arch001-notification-delivery.png");

  for (const name of [
    "Overview",
    "Data Pipeline Monitoring",
    "Compute Health",
    "API Endpoint Monitoring",
    "Alerts",
    "Incidents",
    "Reports",
  ]) {
    await nav(name);
    await page.getByRole("heading", { name, exact: true }).waitFor();
  }
  await nav("Incidents");
  await page.getByLabel("Global environment", { exact: true }).selectOption("");
  await page
    .getByLabel("Incident status", { exact: true })
    .selectOption("OPEN");
  const incidentRow = page.locator("tbody tr").first();
  await incidentRow.getByRole("button").click();
  const incidentId = await incidentRow.locator("small").innerText();
  await page
    .getByRole("heading", { name: "Recovery validation", exact: true })
    .waitFor();
  const ack = response(
    "/api/v1/native-incidents/" + incidentId + "/transition",
    "POST",
  );
  await page
    .getByRole("button", { name: "Acknowledge incident", exact: true })
    .click();
  assert.equal((await ack).status(), 200);
  const note = "Controlled browser investigation " + Date.now();
  await page.getByLabel("Investigation note", { exact: true }).fill(note);
  const savedNote = response(
    "/api/v1/native-incidents/" + incidentId + "/notes",
    "POST",
  );
  await page.getByRole("button", { name: "Add note", exact: true }).click();
  assert.equal((await savedNote).status(), 200);
  await page.getByText(note, { exact: true }).waitFor();
  await shot("arch001-native-incident-investigation.png");
  await page
    .getByRole("button", { name: "Notifications", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Personal notifications", exact: true })
    .waitFor();
  await page
    .getByLabel("Receive in-app notifications", { exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: "Notifications", exact: true })
    .click();
  await nav("Reports");
  for (const name of [
    "Data Pipeline Reports",
    "Compute Health Reports",
    "API Endpoint Reports",
  ])
    await page.getByRole("tab", { name, exact: true }).click();
  await shot("arch001-api-reports.png");
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
  await nav("Resource Management");
  for (const theme of ["Light theme", "Dark theme"]) {
    await page.getByRole("button", { name: theme, exact: true }).click();
    assert.equal(
      await page.evaluate(() => document.documentElement.dataset.theme),
      theme.startsWith("Light") ? "light" : "dark",
    );
    await shot(
      "arch001-" + theme.split(" ")[0].toLowerCase() + "-resources.png",
    );
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await shot("arch001-mobile-resources.png");
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
  const restricted = await browser.newContext(),
    reader = await restricted.newPage();
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
        screenshots,
        incident_ui: true,
        customer_grants_ui: false,
        rbac: true,
        resource_selector_independent: true,
        compute_wizard_stages: 10,
        server_registry: true,
        server_draft_resume: true,
        notification_destination_persisted: true,
        unverified_activation_rejected: true,
      },
      null,
      2,
    ),
  );
  console.log(
    "ARCH-001 V1.5 actual browser, registry, ten-stage wizard, drafts, configuration, reports and access negatives PASS",
  );
} finally {
  await browser.close();
}
