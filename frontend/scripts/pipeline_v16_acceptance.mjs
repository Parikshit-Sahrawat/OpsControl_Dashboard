import assert from "node:assert/strict";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  )
);
const fixture = JSON.parse(
  await readFile(
    join(process.env.V16_PRIVATE_DIR, "browser-fixture.json"),
    "utf8",
  ),
);
const out = process.env.V16_EVIDENCE_DIR;
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
    ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
    : {}),
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
const steps = [
  "General",
  "Platform",
  "Connection",
  "Integration",
  "Collection Sources",
  "Job Discovery/Selection",
  "Source Associations",
  "Validate & Activate",
];
async function navigate() {
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: "Resource Management", exact: true })
    .click();
  await page.getByRole("tab", { name: "Data Pipelines", exact: true }).click();
}
try {
  await page.goto(process.env.V16_UI_URL);
  await page.getByLabel("Username", { exact: true }).fill("v16-api-admin");
  await page.getByLabel("Password", { exact: true }).fill(fixture.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  await navigate();
  const panel = page.getByRole("region", {
    name: "Data Pipelines integrations",
    exact: true,
  });
  await panel
    .getByRole("button", { name: "Create Data Pipeline", exact: true })
    .click();
  const wizard = page.getByRole("region", {
    name: "Data Pipelines eight-step wizard",
    exact: true,
  });
  const nav = wizard.getByRole("navigation", { name: "Data Pipeline steps" });
  assert.equal(await nav.getByRole("button").count(), 8);
  for (let i = 0; i < steps.length; i++)
    await nav
      .getByRole("button", { name: `${i + 1}. ${steps[i]}`, exact: true })
      .click();
  await nav.getByRole("button", { name: "1. General", exact: true }).click();
  const name = "Controlled browser draft " + Date.now();
  await wizard.getByLabel("Integration name", { exact: true }).fill(name);
  await wizard
    .getByLabel("Organization", { exact: true })
    .selectOption(fixture.organization_id);
  await nav.getByRole("button", { name: "2. Platform", exact: true }).click();
  await wizard
    .getByLabel("Platform family", { exact: true })
    .selectOption("AIRFLOW");
  await nav.getByRole("button", { name: "3. Connection", exact: true }).click();
  await wizard.getByLabel(/Base url/i).fill("https://airflow.example.test");
  const saved = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === "/api/v1/data-pipelines/integrations" &&
      r.request().method() === "POST",
  );
  await wizard
    .getByRole("button", { name: "Save / resume draft", exact: true })
    .click();
  assert.equal((await saved).status(), 201);
  await wizard
    .getByRole("button", { name: "Close configuration", exact: true })
    .click();
  await page.reload();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  await navigate();
  await panel.getByLabel("Search integrations", { exact: true }).fill(name);
  await panel.getByRole("button", { name, exact: true }).click();
  await wizard.getByLabel(/Base url/i).waitFor();
  assert.equal(
    await wizard.getByLabel(/Base url/i).inputValue(),
    "https://airflow.example.test",
  );
  await nav
    .getByRole("button", { name: "8. Validate & Activate", exact: true })
    .click();
  assert.equal(
    await wizard
      .getByRole("button", { name: "Activate monitoring", exact: true })
      .isDisabled(),
    true,
  );
  await page.screenshot({
    path: join(out, "pipeline-v16-wizard.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 820 });
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
    true,
  );
  await page.screenshot({
    path: join(out, "pipeline-v16-mobile.png"),
    fullPage: true,
  });
  assert.deepEqual(errors, []);
  await writeFile(
    join(out, "browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        origin: "ACTUAL_PLAYWRIGHT_OWNED_API",
        steps: 8,
        clickable_steps: true,
        draft_connection_resume: true,
        unverified_activation_disabled: true,
        mobile_no_overflow: true,
        vendor_environments_accessed: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "V1.6 actual browser eight-step/draft/activation/mobile acceptance PASS",
  );
} finally {
  await browser.close();
}
