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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const manifest = [];
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
page.on("requestfailed", request => {
  if (request.url().includes(":8000")) errors.push("API request failed: " + request.url() + " - " + request.failure()?.errorText);
});

const categories = [
  ["Overview", "01-overview"],
  ["ETL Jobs", "02-etl-jobs"],
  ["VM Health", "03-vm-health"],
  ["APIs", "04-apis"],
  ["Incidents", "05-incidents"],
  ["Reports", "06-reports"],
  ["Resource Management", "10-resource-management"]
];

async function capture(name, file) {
  await page.waitForTimeout(750);
  const placeholder = await page.locator(".card.placeholder").count() > 0;
  const errorBanners = await page.locator(".error-banner").allTextContents();
  if (errorBanners.length) errors.push(name + ": " + errorBanners.join("; "));
  const heading = await page.locator("h1").first().textContent().catch(() => null);
  const filename = file + ".png";
  await page.screenshot({ path: path.join(output, filename), fullPage: true });
  manifest.push({ name, filename, heading: heading?.trim(), placeholder,
    errorBanners, classification: placeholder ? "navigation placeholder" : "implemented UI view (behavior unverified)" });
}

try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.getByRole("textbox", { name: "Username" }).fill("test-north");
  await page.getByLabel("Password").fill("testing-only-StrongPassword-123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForSelector("button.nav-button", { timeout: 30000 });

  for (const [label, filename] of categories) {
    await page.locator("button.nav-button").filter({ hasText: label }).click();
    await capture(label, filename);
  }
  await page.waitForTimeout(1500);
  for (const [label, filename] of [
    ["Organizations", "11-organizations"],
    ["Data Sources", "12-data-sources"],
    ["Collectors", "13-collectors"],
    ["Templates", "14-templates"]
  ]) {
    await page.locator("button.resource-tab").filter({ hasText: label }).click();
    await capture("Resource Management / " + label, filename);
  }
} finally {
  await writeFile(path.join(output, "manifest.json"), JSON.stringify({ screenshots: manifest, pageErrors: errors }, null, 2));
  await browser.close();
}
console.log(JSON.stringify({ screenshots: manifest, pageErrors: errors }, null, 2));
if (errors.length) process.exitCode = 1;
