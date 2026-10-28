/**
 * Browser evidence for Phase 1 staging review.
 * Captures real rendered pages; never calls a screenshot a completed feature.
 */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const output = path.resolve("phase1-screenshots");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const manifest = [];
const errors = [];
page.on("pageerror", (error) => errors.push(String(error)));
page.on("response", (response) => {
  if (response.url().includes(":8000") && response.status() >= 400)
    errors.push(response.status() + " " + response.url());
});
page.on("requestfailed", (request) => {
  // Scoped polling is cancelled when a tab unmounts or organization changes.
  if (request.failure()?.errorText === "net::ERR_ABORTED") return;
  if (request.url().includes(":8000"))
    errors.push(
      "API request failed: " +
        request.url() +
        " - " +
        request.failure()?.errorText,
    );
});

const categories = [
  ["Overview", "01-overview"],
  ["Data Pipeline Monitoring", "02-etl-jobs"],
  ["Compute Health", "03-vm-health"],
  ["API Endpoint Monitoring", "04-apis"],
  ["Alerts", "05-alerts"],
  ["Reports", "06-reports"],
  ["Data Sources / Resources", "10-resource-management"],
];
const navigationLabel = {
  Overview: "Overview",
  "Data Pipeline Monitoring": "Data Pipeline Monitoring",
  "Compute Health": "Compute Health",
  "API Endpoint Monitoring": "API Endpoint Monitoring",
};

async function capture(name, file) {
  await page.waitForTimeout(750);
  const placeholder = (await page.locator(".card.placeholder").count()) > 0;
  const errorBanners = await page.locator(".error-banner").allTextContents();
  if (errorBanners.length) errors.push(name + ": " + errorBanners.join("; "));
  const heading = await page
    .locator("h1")
    .first()
    .textContent()
    .catch(() => null);
  const filename = file + ".png";
  await page.screenshot({ path: path.join(output, filename), fullPage: true });
  manifest.push({
    name,
    filename,
    heading: heading?.trim(),
    placeholder,
    errorBanners,
    classification: placeholder
      ? "navigation placeholder"
      : "implemented UI view (behavior unverified)",
  });
}

try {
  await page.goto("http://127.0.0.1:5173", {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  await page.getByRole("textbox", { name: "Username" }).fill("test-north");
  await page.getByLabel("Password").fill("testing-only-StrongPassword-123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator(".org-context-button").click();
  await page.locator(".org-option").filter({ hasNotText: "Select every listed customer" }).last().getByRole("checkbox").check();
  try {
    await page.waitForSelector("button.nav-button", { timeout: 20000 });
  } catch (error) {
    throw new Error(
      "Authenticated UI failed: " +
        (await page.locator("body").innerText()) +
        " / " +
        String(error) +
        " pageErrors=" +
        errors.join(" | "),
    );
  }

  for (const [label, filename] of categories) {
    await page.getByRole("button", { name: navigationLabel[label] || label, exact: true }).click();
    await capture(label, filename);
  }
  await page.waitForTimeout(1500);
  for (const [section, domains] of [
    [
      "Data Resources",
      ["Compute Instances", "Data Pipelines", "API Endpoints"],
    ],
    [
      "Alert Rules",
      [
        "Compute Instances Alert Setup",
        "Data Pipelines Alert Setup",
        "API Endpoints Alert Setup",
      ],
    ],
    ["Notification Delivery", []],
  ]) {
    // RM-DEF-034 removes the standalone Event Parameters entry; retain
    // all remaining Resource Management visual/smoke coverage.
    const selector = page.getByLabel("Resource Management component");
    if (section === "Data Resources") {
      if ((await selector.locator('option[value="parameters"]').count()) !== 0) {
        throw new Error("Standalone Event Parameters option unexpectedly present");
      }
    }
    await selector.selectOption({ label: section === "Data Resources" ? "Data Sources / Resources" : section });
    if (!domains.length)
      await capture(
        "Resource Management / " + section,
        "14-notification-delivery",
      );
    for (const domain of domains) {
      await page.getByRole("tab", { name: domain, exact: true }).click();
      await capture(
        "Resource Management / " + section + " / " + domain,
        "11-" +
          section.toLowerCase().replaceAll(" ", "-") +
          "-" +
          domain.toLowerCase().replaceAll(" ", "-"),
      );
    }
  }
} finally {
  await writeFile(
    path.join(output, "manifest.json"),
    JSON.stringify({ screenshots: manifest, pageErrors: errors }, null, 2),
  );
  await browser.close();
}
console.log(
  JSON.stringify({ screenshots: manifest, pageErrors: errors }, null, 2),
);
if (errors.length) process.exitCode = 1;
