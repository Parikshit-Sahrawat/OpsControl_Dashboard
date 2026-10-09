import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
async function login(username) {
  await page.getByRole("textbox", { name: "Username" }).fill(username);
  await page.getByLabel("Password").fill("testing-only-StrongPassword-123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForSelector("button.nav-button", { timeout: 20000 });
}
try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "domcontentloaded" });
  await login("test-reader");
  if (await page.getByRole("button", { name: "Access Management" }).count()) {
    throw new Error("Viewer was offered platform administration navigation");
  }
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("button", { name: "Sign in" }).waitFor();
  await login("test-admin");
  const nav = page.getByRole("button", { name: "Access Management" });
  await nav.waitFor();
  await nav.click();
  await page.getByRole("heading", { name: "Access Management" }).waitFor();
  await page.locator("table tbody tr td").getByText("test-north", { exact: true }).first().waitFor();
  await page.getByText("Organization memberships").first().waitFor();
  if (errors.length) throw new Error(errors.join("; "));
  console.log(JSON.stringify({ status: "PASS", viewerAdminNavigation: false, adminPortalRendered: true }));
} finally {
  await browser.close();
}
