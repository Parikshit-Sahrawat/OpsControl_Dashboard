// Read-only acceptance against a disposable synthetic UAT state.
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const state = process.env.OPSCONTROL_UAT_STATE_DIR;
if (!state) throw new Error("OPSCONTROL_UAT_STATE_DIR is required");
const settings = JSON.parse(fs.readFileSync(path.join(state, "settings.json"), "utf8"));
if (!settings.project?.startsWith("opscontrol-s14-uat-")) throw new Error("Owned UAT project required");
const password = fs.readFileSync(path.join(state, "admin-password"), "utf8").trim();
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || "/workspace/.golden-tools/node_modules/playwright/index.mjs").href);
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium", args: ["--no-sandbox"] });
let passed = 0;
const check = (condition, label) => { assert.ok(condition, label); passed++; console.log(`PASS ${label}`); };
try {
  const page = await browser.newPage({ viewport: { width: 1366, height: 850 } });
  await page.goto(`http://127.0.0.1:${settings.ui_port}`);
  await page.getByLabel("Username").fill("demo-admin");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByText("Signed in as demo-admin").waitFor();
  await page.getByRole("navigation", { name: "Primary navigation" }).getByRole("button", { name: "Departments", exact: true }).click();
  await page.getByRole("button", { name: "Guided Department → Employee → Permissions" }).click();
  const wizard = page.getByRole("dialog", { name: "Department Employee Permissions onboarding" });
  await wizard.waitFor();
  check(await wizard.getByRole("button", { name: /3\. Permissions/ }).isDisabled(), "permissions step requires a provider department");
  const departments = wizard.getByLabel("Select existing department");
  const choice = await departments.locator("option[value]:not([value=''])").first().getAttribute("value");
  assert.ok(choice, "synthetic provider department is required");
  await departments.selectOption(choice);
  await wizard.getByRole("button", { name: "Find existing employee in this department" }).click();
  check(await wizard.getByLabel("Search existing employees").count() === 1, "permissions step has a single employee search control");
  check(await wizard.getByRole("combobox", { name: "Employee", exact: true }).count() === 0, "redundant employee selector is removed");
  await wizard.getByRole("button", { name: "Close onboarding" }).click();
  console.log(`RESULT ${passed} passed, 0 failed; no role or employee mutation`);
} finally { await browser.close(); }
