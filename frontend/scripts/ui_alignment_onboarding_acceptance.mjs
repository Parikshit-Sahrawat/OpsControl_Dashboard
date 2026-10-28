// Run only against a disposable synthetic UAT state created by local_environment.py.
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const state = process.env.OPSCONTROL_UAT_STATE_DIR;
if (!state) throw new Error("OPSCONTROL_UAT_STATE_DIR is required");
const settings = JSON.parse(fs.readFileSync(path.join(state, "settings.json"), "utf8"));
if (!settings.project?.startsWith("opscontrol-s14-uat-"))
  throw new Error("Refusing non-UAT environment");
const password = fs.readFileSync(path.join(state, "admin-password"), "utf8").trim();
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || "/workspace/.golden-tools/node_modules/playwright/index.mjs").href);
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium", args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
const evidenceDir = process.env.UI_ALIGNMENT_EVIDENCE_DIR;
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; console.log(`PASS ${message}`); };
try {
  await page.goto(`http://127.0.0.1:${settings.ui_port}`);
  await page.getByLabel("Username").fill("demo-admin");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Signed in as demo-admin").waitFor();
  const nav = page.getByRole("navigation", { name: "Primary navigation" });
  await nav.getByRole("button", { name: "Data Sources / Resources", exact: true }).click();
  await page.getByRole("button", { name: "Create Compute Instance" }).click();
  const workspace = page.getByRole("region", { name: "Create Compute Instance" });
  await workspace.waitFor();
  await workspace.getByText("Loading attribute definitions…").waitFor({ state: "hidden" });
  const suffix = Date.now().toString(36);
  await workspace.getByLabel("Resource name").fill(`Synthetic UI acceptance ${suffix}`);
  await workspace.getByLabel("Customer", { exact: true }).selectOption({ label: "Synthetic UAT Customer A" });
  await workspace.getByLabel("Hostname").fill(`ui-acceptance-${suffix}.example.test`);
  await workspace.getByLabel("DNS / IP address").fill(`ui-acceptance-${suffix}.example.test`);
  check(await workspace.locator(".onboarding-step").count() === 0, "VM identity editor has no inactive wizard sidebar");
  await workspace.getByRole("button", { name: "Save resource identity" }).click();
  await workspace.waitFor({ state: "hidden" });
  await page.getByLabel("Search resources", { exact: true }).fill(`Synthetic UI acceptance ${suffix}`);
  const resourceRow = page.getByRole("row").filter({ hasText: `Synthetic UI acceptance ${suffix}` });
  await resourceRow.waitFor();
  await resourceRow.getByRole("button", { name: "Collector Configuration" }).click();
  await page.getByText("Collection Methods", { exact: false }).first().waitFor();
  check(true, "new host Collector is accessible from saved resource identity");
  await page.getByRole("button", { name: "Close Collector Details" }).click();
  if (evidenceDir) {
    fs.mkdirSync(evidenceDir, { recursive: true });
    await page.screenshot({ path: path.join(evidenceDir, "compute-synthetic-identity-and-methods.png"), fullPage: true });
  }
  console.log(`RESULT ${checks} passed, 0 failed; synthetic UAT resource only; no agent or monitoring activation`);
} finally {
  await browser.close();
}
