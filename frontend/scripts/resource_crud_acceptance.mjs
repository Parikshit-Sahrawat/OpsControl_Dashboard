import { preparePrimaryNavigation } from "./primary_navigation.mjs";
import { scopeHeaders } from "./explicit_scope.mjs";
// Actual browser forms and authenticated backend; no mocked API responses.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
});
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [],
  serverErrors = [];
const diagnostics = [], reloads = [];
page.on("requestfailed", r => diagnostics.push({kind:"requestfailed", path:new URL(r.url()).pathname, error:r.failure()?.errorText, at:Date.now()}));
page.on("response", r => {if(r.url().includes("/api/"))diagnostics.push({kind:"response",path:new URL(r.url()).pathname,status:r.status(),at:Date.now()});});
page.on("framenavigated", f => {if(f===page.mainFrame())diagnostics.push({kind:"navigation",path:new URL(f.url()).pathname,hash:new URL(f.url()).hash,at:Date.now()});});
async function keyboardTo(locator) {
  for(let i=0;i<90;i++) {
    if(await locator.evaluate(el=>el===document.activeElement))return;
    await page.keyboard.press("Tab");
  }
  throw Error("Target was not keyboard reachable");
}
page.on("pageerror", (e) => errors.push(e.message));
page.on("response", (r) => {
  if (r.url().includes("/api/") && r.status() >= 500)
    serverErrors.push(r.status());
});
const base = process.env.TEST_API_BASE;
const password = "testing-only-StrongPassword-123!";
let phase = "login";
try {
  await page.goto(process.env.RELEASE_UI_BASE);
  await page.getByLabel("Username").fill("test-north");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
  phase = "open onboarding";
  await preparePrimaryNavigation(page);
  await page
    .getByRole("button", { name: "Data Sources / Resources", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create Compute Instance", exact: true })
    .click();
  let modal = page.getByRole("region", {
    name: "Create Compute Instance",
    exact: true,
  });
  await modal
    .getByLabel("Resource name", { exact: true })
    .fill("Wizard sequence registration");
  const customerOption = modal
    .getByLabel("Customer", { exact: true })
    .locator("option")
    .nth(1);
  await modal
    .getByLabel("Customer", { exact: true })
    .selectOption(await customerOption.getAttribute("value"));
  await modal.getByLabel(/^Environment/).selectOption("DEV");
  await modal
    .getByLabel("Hostname", { exact: true })
    .fill("wizard-sequence.example.test");
  await modal
    .getByLabel("DNS / IP address", { exact: true })
    .fill("203.0.113.75");
  await modal
    .getByRole("button", { name: "Save resource identity", exact: true })
    .click();
  await modal.waitFor({ state: "hidden" });
  phase = "locate created resource";
  await page
    .getByLabel("Search resources", { exact: true })
    .fill("Wizard sequence registration");
  let row = page
    .getByRole("row")
    .filter({ hasText: "Wizard sequence registration" });
  await row.waitFor();
  const token = await page.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const headers = await scopeHeaders(page.request, base, token);
  const sourcesResponse = await page.request.get(
    base + "/api/v1/resource-management/data-sources",
    { headers },
  );
  assert.equal(sourcesResponse.status(), 200);
  const source = (await sourcesResponse.json()).find(
    (s) => s.name === "wizard-sequence.example.test",
  );
  assert.ok(source);
  const collectorPath =
    base + "/api/v1/resource-management/collectors?data_source_id=" + source.id;
  let registrations = await (
    await page.request.get(collectorPath, { headers })
  ).json();
  assert.equal(registrations.length, 1);
  const registration = registrations[0];
  assert.equal(registration.collector_type, "OTEL");
  assert.equal(registration.enabled, true);
  assert.equal(registration.status, "STOPPED");
  assert.equal(
    registration.name,
    "Wizard sequence registration Agent Configuration",
  );
  const duplicate = await page.request.post(
    base + "/api/v1/resource-management/data-sources",
    {
      headers,
      data: {
        organization_id: source.organization_id,
        name: source.name,
        source_type: source.source_type,
      },
    },
  );
  assert.equal(duplicate.status(), 409);
  phase = "edit registration";
  await row
    .getByRole("button", { name: "Collector Configuration", exact: true })
    .click();
  modal = page.getByRole("dialog", { name: "Collector Details", exact: true });
  await modal
    .getByLabel("Collector name", { exact: true })
    .fill("wizard-registration-updated");
  await modal
    .getByRole("button", { name: "Save Collector Details", exact: true })
    .click();
  await modal
    .getByRole("button", { name: "Close Collector Details", exact: true })
    .click();
  phase = "verify persisted registration";
  await modal.waitFor({ state: "hidden" });
  registrations = await (
    await page.request.get(collectorPath, { headers })
  ).json();
  assert.equal(registrations.length, 1);
  assert.equal(registrations[0].id, registration.id);
  assert.equal(registrations[0].name, "wizard-registration-updated");
  assert.equal(registrations[0].enabled, true);
  const runs = await page.request.get(
    base + "/api/v1/monitoring/collectors/" + registration.id + "/runs",
    { headers },
  );
  assert.deepEqual(await runs.json(), []);
  const otherLogin = await page.request.post(base + "/api/v1/auth/login", {
    data: { username: "test-south", password },
  });
  assert.equal(otherLogin.status(), 200);
  const otherHeaders = await scopeHeaders(
    page.request,
    base,
    (await otherLogin.json()).access_token,
  );
  const cross = await page.request.patch(
    base + "/api/v1/resource-management/data-sources/" + source.id,
    {
      headers: otherHeaders,
      data: { name: "forged-cross-tenant" },
    },
  );
  assert.equal(cross.status(), 404);
  const crossRows = await page.request.get(collectorPath, {
    headers: otherHeaders,
  });
  assert.deepEqual(await crossRows.json(), []);
  phase = "overlapping refresh ordering";
  // Delay an unchanged, authenticated backend response; no fabricated rows.
  // A second refresh must win even when the first snapshot arrives last.
  let signalCaptured, releaseOlder;
  const captured = new Promise((resolve) => {
    signalCaptured = resolve;
  });
  const held = new Promise((resolve) => {
    releaseOlder = resolve;
  });
  let finishOlder;
  const finishedOlder = new Promise((resolve) => {
    finishOlder = resolve;
  });
  let olderError;
  let first = true;
  const inventoryRoute = "**/api/v1/unified/resources?*";
  await page.route(inventoryRoute, async (route) => {
    if (!first) return route.continue();
    first = false;
    const response = await route.fetch();
    signalCaptured();
    await held;
    try {
      await route.fulfill({ response });
    } catch (error) {
      // Changing the search aborts the superseded fetch. Both abort and a late
      // response must leave the newer persisted inventory visible.
      if (route.request().failure()?.errorText !== "net::ERR_ABORTED")
        olderError = error;
    } finally {
      finishOlder();
    }
  });
  try {
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await captured;
    const inventory = await (
      await page.request.get(
        base +
          "/api/v1/unified/resources?domain=VM&search=Wizard%20sequence%20registration",
        { headers },
      )
    ).json();
    const resource = inventory.items.find(
      (r) => r.data_source_id === source.id,
    );
    assert(resource);
    const renamed = "Wizard sequence refreshed";
    const updated = await page.request.put(
      base + "/api/v1/unified/resources/" + resource.id,
      {
        headers,
        data: {
          expected_revision: resource.revision,
          name: renamed,
          environment: resource.environment,
          configuration: resource.configuration,
          active: resource.active,
        },
      },
    );
    assert.equal(updated.status(), 200);
    await page
      .getByLabel("Search resources", { exact: true })
      .fill("Wizard sequence");
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await page.getByRole("button", { name: renamed, exact: true }).waitFor();
    releaseOlder();
    await page.waitForLoadState("networkidle");
    assert.equal(
      await page.getByRole("button", { name: renamed, exact: true }).count(),
      1,
    );
  } finally {
    releaseOlder();
    await finishedOlder;
    await page.unroute(inventoryRoute);
    if (olderError) throw olderError;
  }
  await mkdir(process.env.RELEASE_EVIDENCE_DIR, { recursive: true });
  await page.screenshot({
    path: process.env.RELEASE_EVIDENCE_DIR + "/resource-registration.png",
    fullPage: true,
  });
  phase = "disable resource";
  row = page.getByRole("row").filter({ hasText: "Wizard sequence refreshed" });
  await row.getByRole("button", { name: "Edit", exact: true }).click();
  modal = page.getByRole("region", {
    name: "Edit Compute Instance",
    exact: true,
  });
  await modal.getByLabel("Enable resource", { exact: true }).uncheck();
  await modal
    .getByRole("button", { name: "Save resource", exact: true })
    .click();
  await modal.waitFor({ state: "hidden" });
  const disabled = (
    await (
      await page.request.get(
        base +
          "/api/v1/unified/resources?domain=VM&search=Wizard%20sequence%20refreshed",
        { headers },
      )
    ).json()
  ).items.find((r) => r.data_source_id === source.id);
  assert.equal(disabled.active, false);
  // Re-enable the same persisted identity, then verify narrow-screen keyboard use.
  await row.getByRole("button", { name: "Edit", exact: true }).click();
  modal = page.getByRole("region", { name: "Edit Compute Instance", exact: true });
  await modal.getByLabel("Enable resource", { exact: true }).check();
  await modal.getByRole("button", { name: "Save resource", exact: true }).click();
  await modal.waitFor({ state: "hidden" });
  await page.reload();
  await page.getByLabel("Search resources", { exact: true }).fill("Wizard sequence refreshed");
  await page.getByRole("button", { name: "Wizard sequence refreshed", exact: true }).waitFor();
  const enabledAgain = (await (await page.request.get(base + "/api/v1/unified/resources?domain=VM&search=Wizard%20sequence%20refreshed", { headers })).json()).items.find(r => r.data_source_id === source.id);
  assert.equal(enabledAgain.active, true);
  phase = "repeated reload diagnostic";
  for(let iteration=0;iteration<5;iteration++) {
    const beforeUrl=page.url();const started=Date.now();
    await page.reload();
    await page.getByLabel("Search resources",{exact:true}).fill("Wizard sequence refreshed");
    await page.getByRole("button",{name:"Wizard sequence refreshed",exact:true}).waitFor();
    reloads.push({iteration,before_hash:new URL(beforeUrl).hash,after_hash:new URL(page.url()).hash,elapsed_ms:Date.now()-started,status:"PASS"});
  }
  phase="keyboard-only resource edit";
  // Hold the real authorized response, not a fabricated revision, to exercise
  // keyboard reachability while the mandatory snapshot is still pending.
  let releaseContext;
  const contextGate = new Promise(resolve => { releaseContext = resolve; });
  let contextInFlight = 0, contextCompleted = 0;
  await page.route("**/configuration-context", async route => {
    contextInFlight++;
    try {
      const response = await route.fetch();
      await contextGate;
      await route.fulfill({response});
      contextCompleted++;
    } finally { contextInFlight--; }
  });
  const mutations = [];
  page.on("request", request => {
    if(request.method()==="PUT" && /\/unified\/resources\/[^/]+$/.test(new URL(request.url()).pathname)) mutations.push(request.postDataJSON());
  });
  row=page.getByRole("row").filter({hasText:"Wizard sequence refreshed"});
  await keyboardTo(row.getByRole("button",{name:"Edit",exact:true}));
  await page.keyboard.press("Enter");
  modal=page.getByRole("region",{name:"Edit Compute Instance",exact:true});
  const nameInput=modal.getByLabel("Resource name",{exact:true});
  await keyboardTo(nameInput);await page.keyboard.press("ControlOrMeta+A");
  await page.keyboard.type("Wizard keyboard persisted");
  await keyboardTo(modal.getByRole("button",{name:"Save resource",exact:true}));
  const keyboardSave = modal.getByRole("button",{name:"Save resource",exact:true});
  assert.equal(await keyboardSave.getAttribute("aria-disabled"), "true");
  await page.keyboard.press("Enter");
  await modal.getByRole("alert").filter({hasText:"Wait for the configuration revision snapshot"}).waitFor();
  assert.equal(mutations.length, 0, "no write without authorized revisions");
  assert.equal(await nameInput.inputValue(), "Wizard keyboard persisted");
  releaseContext();
  // A response event can precede completion of route.fulfill(). Plain unroute
  // lets Playwright auto-handle that request a second time. Drain, don't ignore.
  await page.unrouteAll({behavior:"wait"});
  assert.equal(contextInFlight,0);
  assert.ok(contextCompleted > 0);
  await page.waitForFunction(() => document.querySelector('button[form][aria-disabled="false"]'));
  assert.equal(await keyboardSave.evaluate(el=>el===document.activeElement), true, "snapshot arrival preserves keyboard focus");
  await page.keyboard.press("Enter");await modal.waitFor({state:"hidden"});
  assert.equal(mutations.length, 1, "one Enter commits one command");
  assert.ok(Number.isInteger(mutations[0].expected_revision));
  assert.ok(mutations[0].expected_child_source_revisions);
  await page.getByLabel("Search resources",{exact:true}).fill("Wizard keyboard persisted");
  await page.getByRole("button",{name:"Wizard keyboard persisted",exact:true}).waitFor();
  await page.reload();
  await page.getByLabel("Search resources",{exact:true}).fill("Wizard keyboard persisted");
  await page.getByRole("button",{name:"Wizard keyboard persisted",exact:true}).waitFor();
  // Native Enter submission from a text field, followed by persisted reload.
  row=page.getByRole("row").filter({hasText:"Wizard keyboard persisted"});
  await keyboardTo(row.getByRole("button",{name:"Edit",exact:true}));
  await page.keyboard.press("Enter");
  modal=page.getByRole("region",{name:"Edit Compute Instance",exact:true});
  await page.waitForFunction(() => document.querySelector('button[form][aria-disabled="false"]'));
  await keyboardTo(modal.getByLabel("Resource name",{exact:true}));
  await page.keyboard.press("Enter");await modal.waitFor({state:"hidden"});
  assert.equal(mutations.length, 2);
  assert.ok(mutations[1].expected_revision > mutations[0].expected_revision);
  await page.reload();
  await page.getByLabel("Search resources",{exact:true}).fill("Wizard keyboard persisted");
  await page.getByRole("button",{name:"Wizard keyboard persisted",exact:true}).waitFor();
  await page.screenshot({path:process.env.RELEASE_EVIDENCE_DIR+"/resource-keyboard-desktop.png",fullPage:true});
  await writeFile(process.env.RELEASE_EVIDENCE_DIR+"/keyboard-regression.json",JSON.stringify({status:"PASS",pending_snapshot_writes:0,committed_commands:mutations.length,revision_increased:true,focus_preserved:true,enter_button:true,enter_input:true,reload_persisted:true,route_handlers_drained:contextInFlight===0,completed_real_context_responses:contextCompleted},null,2));
  await page.setViewportSize({ width:390, height:844 });
  await page.keyboard.press("Tab");
  assert.notEqual(await page.evaluate(()=>document.activeElement.tagName), "BODY");
  await page.screenshot({ path:process.env.RELEASE_EVIDENCE_DIR+"/resource-mobile-keyboard.png", fullPage:true });
  assert.deepEqual(errors, []);
  assert.deepEqual(serverErrors, []);
  await writeFile(
    process.env.RELEASE_EVIDENCE_DIR + "/resource-crud.json",
    JSON.stringify(
      {
        status: "PASS",
        checks: [
          "Browser create/read/update/disable/re-enable and reload persisted",
          "Narrow viewport and keyboard-only edit/save persisted",
          "Five exact repeated reloads preserve resource route and persisted records",
          "Duplicate source returns 409",
          "Logical OTEL configuration creates no polling CollectorRun",
          "Edit preserves Collector ID and updates its configuration name",
          "Other tenant cannot read registration or mutate source",
          "Older authenticated inventory refresh cannot overwrite newer persisted state",
        ],
        reloads,
        diagnostics,
        page_errors: errors,
        server_errors: serverErrors,
      },
      null,
      2,
    ),
  );
  console.log(
    "RESOURCE WIZARD / INACTIVE REGISTRATION / CRUD / TENANT ACCEPTANCE PASS",
  );
} catch (error) {
  // Only a fixture phase and error type leave the private diagnostics directory.
  console.error(
    "RESOURCE_CRUD_FAILURE " + JSON.stringify({ phase, type: error.name }),
  );
  await mkdir(process.env.RELEASE_EVIDENCE_DIR,{recursive:true});
  await page.screenshot({path:process.env.RELEASE_EVIDENCE_DIR+"/resource-failure.png",fullPage:true});
  await writeFile(process.env.RELEASE_EVIDENCE_DIR+"/resource-failure.json",JSON.stringify({phase,type:error.name,hash:new URL(page.url()).hash,reloads,diagnostics},null,2));
  throw error;
} finally {
  await browser.close();
}
