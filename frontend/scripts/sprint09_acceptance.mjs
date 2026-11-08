import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  )
);
const f = JSON.parse(
  await readFile(
    join(process.env.V16_PRIVATE_DIR, "sprint09-fixture.json"),
    "utf8",
  ),
);
const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
});
const page = await browser.newPage({ viewport: { width: 1400, height: 960 } }),
  errors = [],
  checks = [];
page.setDefaultTimeout(25000);
page.on("pageerror", (e) => errors.push(e.message));
async function shot(name) {
  await page.screenshot({
    path: join(process.env.V16_EVIDENCE_DIR, "sprint09-" + name + ".png"),
    fullPage: true,
  });
}
async function route(key) {
  await page.goto(process.env.V16_UI_URL + "/#/pipelines/" + key);
}
try {
  await page.addInitScript(
    (id) =>
      localStorage.setItem("opscontrol.organizationIds", JSON.stringify([id])),
    f.organization,
  );
  await route("inventory");
  await page.getByLabel("Username", { exact: true }).fill(f.username);
  await page.getByLabel("Password", { exact: true }).fill(f.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", {name:"Pipeline Inventory",exact:true}).waitFor();
  await page.getByRole("navigation", {name:"Pipeline operational pages"}).getByRole("link", {name:"Execution History",exact:true}).click();
  await page.getByRole("heading", {name:"Execution History",exact:true}).waitFor();
  await page
    .getByLabel("Find pipeline", { exact: true })
    .fill("Sprint 09 archive pipeline");
  await page
    .getByRole("button", { name: "Search pipelines", exact: true })
    .click();
  await page
    .getByRole("option", { name: /Sprint 09 archive pipeline/ })
    .waitFor({ state: "attached" });
  await page
    .getByLabel("Selected pipeline", { exact: true })
    .selectOption(f.resource);
  const result = page.waitForResponse(
    (r) => r.url().includes("outcome=SUCCESS") && r.status() === 200,
  );
  await page.getByLabel("Execution outcome").selectOption("SUCCESS");
  const body = await (await result).json();
  assert.equal(body.total, 1);
  await page
    .getByRole("region", { name: "Execution history", exact: true })
    .getByRole("button", { name: f.history, exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Execution details",
    exact: true,
  });
  await dialog.getByRole("button", { name: "Audit", exact: true }).click();
  const retained = page.getByRole("region", {
    name: "Retained attempt evidence",
  });
  await retained.getByLabel("Evidence collection").selectOption("aliases");
  await retained
    .getByText(/INVOCATION/)
    .first()
    .waitFor();
  await retained
    .getByRole("navigation", { name: "Retained evidence pagination" })
    .getByRole("button", { name: "Next page" })
    .click();
  await retained
    .getByRole("navigation", { name: "Retained evidence pagination" })
    .getByText(/21–40 of/)
    .waitFor();
  await shot("attempt-archive");
  checks.push(
    "Server outcome filtering and paginated retained attempt aliases in the real execution drawer",
  );
  await dialog
    .getByRole("button", { name: "Close detail drawer", exact: true })
    .click();
  await route("schedules");
  await page
    .getByRole("heading", { name: "Schedule Monitoring", exact: true })
    .waitFor();
  await page
    .getByLabel("Selected pipeline", { exact: true })
    .selectOption(f.resource);
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText(/of 603/)
    .waitFor();
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByRole("button", { name: "Next page" })
    .click();
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText(/21–40 of 603/)
    .waitFor();
  const filtered = page.waitForResponse(
    (r) =>
      r.url().includes("schedule-occurrences") &&
      r.url().includes("status=NO_RUN") &&
      r.status() === 200,
  );
  await page.getByLabel("Schedule compliance").selectOption("NO_RUN");
  assert.equal((await (await filtered).json()).total, 0);
  await page
    .getByRole("navigation", { name: "Occurrences pagination" })
    .getByText("0–0 of 0", { exact: true })
    .waitFor();
  await shot("schedule-filter");
  checks.push(
    "Schedule paging and server filter keep unknown/incomplete fixture coverage out of NO_RUN",
  );
  await route("incidents");
  await page.getByRole("heading", {name:"Pipeline Inventory",exact:true}).waitFor();
  assert.equal(await page.getByRole("region",{name:"Native incident correlation"}).count(),0);
  assert.equal(await page.getByRole("button",{name:"Incidents",exact:true}).count(),0);
  const token=await page.evaluate(()=>sessionStorage.getItem("opscontrol.sessionToken"));
  const headers={Authorization:"Bearer "+token,"X-OpsControl-Customers":f.organization};
  const endpoint=process.env.V16_API_URL+"/api/v1/native-incidents/"+f.incident+"/activities";
  const first=await page.request.get(endpoint+"?limit=20&offset=0",{headers});assert.equal(first.status(),200);
  const initial=await first.json();assert.ok(initial.total>=205);assert.equal(initial.items.length,20);
  const second=await page.request.get(endpoint+"?limit=20&offset=20",{headers});assert.equal(second.status(),200);
  const next=await second.json();assert.equal(next.total,initial.total);assert.equal(next.items.length,20);
  assert.equal(new Set([...initial.items,...next.items].map(v=>v.id)).size,40);
  const end=await page.request.get(endpoint+"?limit=20&offset="+initial.total,{headers});assert.equal(end.status(),200);assert.equal((await end.json()).items.length,0);
  await shot("retired-incident-route");
  checks.push("Retired incident UI rejected; retained authenticated background activity archive has distinct pages and bounded end");
  assert.deepEqual(errors, []);
  await writeFile(
    join(process.env.V16_EVIDENCE_DIR, "sprint09-browser.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        backend: "Actual local authenticated API and owned PostgreSQL",
        genuine_runtime_acceptance: false,
      },
      null,
      2,
    ),
  );
  console.log(
    "Sprint 09 actual Chromium archive acceptance PASS:",
    checks.length,
    "groups",
  );
} finally {
  await browser.close();
}
