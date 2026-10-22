// Actual Chromium and authenticated backend evidence. No API interception or mocks.
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const { chromium } = await import(
  pathToFileURL(process.env.PLAYWRIGHT_MODULE).href
);
const state = JSON.parse(await readFile(process.env.ETL_SESSION_FILE, "utf8"));
const password = await readFile(
  join(process.env.ETL_PRIVATE_DIR, "admin-password"),
  "utf8",
);
const output = join(process.env.OPERATIONAL_EVIDENCE_DIR, "ui-test-1");
const origin = process.env.UI_THEME_BASE_URL || "http://127.0.0.1:15174";
const storageKey = "opscontrol.theme";
const primaryTabs = [
  "Overview",
  "Data Pipeline Monitoring",
  "Compute Health",
  "API Endpoint Monitoring",
  "Alerts",
  "Incidents",
  "Reports",
  "Resource Management",
];
const headings = {
  Overview: "Dashboard",
  "Data Pipeline Monitoring": "Pipeline Inventory",
  "Resource Management": "Resource Management",
};
const checks = [],
  screenshots = [],
  pageErrors = [],
  serverErrors = [],
  contrast = [];
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
});

async function makePage(options = {}, initialize) {
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1100 },
    ...options,
  });
  if (initialize) await context.addInitScript(initialize);
  const page = await context.newPage();
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 500) {
      serverErrors.push({
        status: response.status(),
        path: new URL(response.url()).pathname,
      });
    }
  });
  return page;
}

async function themeIs(page, mode) {
  await page.waitForFunction(
    (expected) => document.documentElement.dataset.theme === expected,
    mode,
  );
  assert.equal(
    await page
      .getByRole("button", {
        name: `${mode === "dark" ? "Dark" : "Light"} theme`,
        exact: true,
      })
      .getAttribute("aria-pressed"),
    "true",
  );
  const opposite = mode === "dark" ? "Light" : "Dark";
  assert.equal(
    await page
      .getByRole("button", { name: `${opposite} theme`, exact: true })
      .getAttribute("aria-pressed"),
    "false",
  );
}

async function setTheme(page, mode) {
  await page
    .getByRole("button", {
      name: `${mode === "dark" ? "Dark" : "Light"} theme`,
      exact: true,
    })
    .click();
  await themeIs(page, mode);
}

async function login(page, who = "admin") {
  await page.goto(origin);
  await page
    .getByRole("textbox", { name: "Username", exact: true })
    .fill(who === "admin" ? "demo-admin" : state[`${who}_username`]);
  await page
    .getByLabel("Password", { exact: true })
    .fill(who === "admin" ? password : state[`${who}_password`]);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
}

async function chooseOrganization(page, name) {
  await page.locator(".org-context-button").click();
  await page.getByRole("checkbox", { name: new RegExp(`^${name}`) }).check();
  const boxes = page.locator(".org-menu").getByRole("checkbox");
  for (let index = 1; index < (await boxes.count()); index++) {
    const box = boxes.nth(index);
    if (
      !(await box.locator("..").innerText()).startsWith(name) &&
      (await box.isChecked())
    )
      await box.uncheck();
  }
  await page.locator(".org-context-button").click();
}

async function expandExisting(page, label) {
  const show = page.getByRole("button", {name: "Show " + label, exact: true});
  await page.getByRole("button", {name: new RegExp("^(Show|Hide) " + label + "$")}).waitFor();
  if (await show.isVisible()) await show.click();
  await page.getByRole("button", {name: "Hide " + label, exact: true}).waitFor();
}

async function tab(page, name) {
  if (await page.getByRole("button", { name: "Open navigation" }).isVisible())
    await page.getByRole("button", { name: "Open navigation" }).click();
  const destination = name === "Resource Management" ? "Data Sources / Resources"
    : name === "Access Management" ? "Employees" : name;
  await page.getByRole("navigation", { name: "Primary navigation" })
    .getByRole("button", { name: destination, exact: true }).click();
  await page.getByRole("heading", { name: headings[name] || name, exact: true }).waitFor();
  // Wait for actual persisted fixture evidence on each redesigned screen.
  if (name === "Overview") {
    await page
      .getByRole("heading", { name: "Running Data Pipeline Executions" })
      .waitFor();
  } else if (name === "Data Pipeline Monitoring") {
    await page.getByRole("navigation", { name: "Pipeline operational pages" })
      .getByRole("link", { name: "Execution History" }).click();
    await page
      .locator(".pipeline-workspace .card")
      .filter({ has: page.getByRole("heading", { name: "Current Executions" }) })
      .getByRole("row")
      .filter({ hasText: "Fictional Daily Warehouse" })
      .first()
      .waitFor();
  } else if (name === "Compute Health") {
    await expandExisting(page, "infrastructure adapter health");
    await page
      .getByTestId("infrastructure-row")
      .filter({ hasText: "ETL live Linux worker" })
      .waitFor();
  } else if (name === "API Endpoint Monitoring") {
    await expandExisting(page, "service probe health");
    await page
      .getByTestId("service-row")
      .filter({ hasText: "Fictional NOC HTTPS Portal" })
      .waitFor();
  } else if (name === "Alerts") {
    await page
      .getByRole("row")
      .filter({ hasText: "noc-http-unavailable" })
      .first()
      .waitFor();
  } else if (name === "Reports") {
    const observed = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === "/api/v1/unified/reports/API" &&
        r.request().method() === "GET",
    );
    await page
      .getByRole("tab", { name: "API Endpoint Reports", exact: true })
      .click();
    const evidence = await (await observed).json();
    assert(
      evidence.summary.completed_probes > 0,
      "Reports must aggregate actual completed probe evidence",
    );
    await page.locator(`#report-resource-choices option[value="Fictional NOC HTTPS Portal · PROD · ${state.http_source_id}"]`)
      .waitFor({ state: "attached" });
  } else if (name === "Resource Management") {
    await page.getByRole("tab", { name: "API Endpoints", exact: true }).click();
    await page
      .getByRole("row")
      .filter({ hasText: "Fictional NOC HTTPS Portal" })
      .waitFor();
  } else if (name === "Access Management") {
    await page
      .getByRole("row")
      .filter({ hasText: "etl-operator" })
      .first()
      .waitFor();
  }
}

async function screenshot(page, name) {
  await page.screenshot({ path: join(output, `${name}.png`), fullPage: true });
  screenshots.push(`${name}.png`);
}

async function assertNoBodyOverflow(page, label) {
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    body: document.body.scrollWidth,
    document: document.documentElement.scrollWidth,
  }));
  assert.ok(
    dimensions.body <= dimensions.viewport + 1 &&
      dimensions.document <= dimensions.viewport + 1,
    `${label}: page overflow ${JSON.stringify(dimensions)}; wide tables must scroll within their own container`,
  );
}

async function badgeContrast(page, mode) {
  for (const [name, status] of [
    ["Fictional NOC HTTPS Portal", "HEALTHY"],
    ["Unobserved NOC Service", "UNKNOWN"],
    ["Disabled NOC Service", "DISABLED"],
  ]) {
    const badge = page
      .getByTestId("service-row")
      .filter({ hasText: name })
      .getByText(status, { exact: true });
    await badge.waitFor();
    const value = await badge.evaluate((element) => {
      const canvas = document.createElement("canvas");
      canvas.width = 1;
      canvas.height = 1;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      const rgba = (color) => {
        ctx.clearRect(0, 0, 1, 1);
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, 1, 1);
        const result = ctx.getImageData(0, 0, 1, 1).data;
        return [
          result[0] / 255,
          result[1] / 255,
          result[2] / 255,
          result[3] / 255,
        ];
      };
      const blend = (foreground, background) =>
        foreground
          .slice(0, 3)
          .map(
            (value, index) =>
              value * foreground[3] + background[index] * (1 - foreground[3]),
          );
      const ancestors = [];
      let parent = element;
      while (parent) {
        ancestors.unshift(parent);
        parent = parent.parentElement;
      }
      let background = [1, 1, 1];
      for (const node of ancestors)
        background = blend(
          rgba(getComputedStyle(node).backgroundColor),
          background,
        );
      const text = blend(rgba(getComputedStyle(element).color), background);
      const luminance = (rgb) =>
        rgb
          .map((channel) =>
            channel <= 0.04045
              ? channel / 12.92
              : ((channel + 0.055) / 1.055) ** 2.4,
          )
          .reduce(
            (sum, channel, index) =>
              sum + channel * [0.2126, 0.7152, 0.0722][index],
            0,
          );
      const values = [luminance(text), luminance(background)].sort(
        (a, b) => b - a,
      );
      return (values[0] + 0.05) / (values[1] + 0.05);
    });
    contrast.push({ theme: mode, status, ratio: Number(value.toFixed(2)) });
    assert.ok(
      value >= 4.5,
      `${mode} ${status} badge text contrast ${value.toFixed(2)}:1 must reach 4.5:1`,
    );
  }
}

try {
  const page = await makePage({ colorScheme: "dark" });
  await page.goto(origin);
  await themeIs(page, "dark");
  checks.push(
    "Unset preference follows actual browser dark color scheme before authentication",
  );
  await login(page);
  await chooseOrganization(page, "Controlled ETL Lab");

  for (const mode of ["dark", "light"]) {
    await setTheme(page, mode);
    assert.equal(
      await page.evaluate((key) => localStorage.getItem(key), storageKey),
      mode,
    );
    for (const name of [...primaryTabs, "Access Management"]) {
      await tab(page, name);
      await themeIs(page, mode);
      if (["Overview", "API Endpoint Monitoring", "Reports"].includes(name))
        await screenshot(page, `${mode}-${name.toLowerCase()}`);
      if (name === "API Endpoint Monitoring") await badgeContrast(page, mode);
    }
    await tab(page, "API Endpoint Monitoring");
    await page
      .getByTestId("service-row")
      .filter({ hasText: "Fictional NOC HTTPS Portal" })
      .getByRole("button", { name: "Fictional NOC HTTPS Portal", exact: true })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog
      .getByRole("heading", { name: "Operational history", exact: true })
      .waitFor();
    assert.ok(
      (await dialog.getByRole("row").count()) > 1,
      "Service investigation must contain actual collected history",
    );
    await screenshot(page, `${mode}-investigation`);
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "hidden" });
    await tab(page, "Data Pipeline Monitoring");
    await page
      .locator(".pipeline-workspace .card")
      .filter({ has: page.getByRole("heading", { name: "Current Executions" }) })
      .getByRole("row")
      .filter({ hasText: "Fictional Daily Warehouse" })
      .click();
    const execution = page.getByRole("dialog");
    await execution
      .getByRole("button", { name: "Close drawer", exact: true })
      .waitFor();
    await page.keyboard.press("Shift+Tab");
    assert.equal(
      await execution.evaluate((element) =>
        element.contains(document.activeElement),
      ),
      true,
    );
    await page.keyboard.press("Escape");
    await execution.waitFor({ state: "hidden" });
    await tab(page, "Resource Management");
    await page
      .getByRole("tab", { name: "Compute Instances", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Create Compute Instance", exact: true })
      .click();
    const resource = page.getByRole("region", {
      name: "Create Compute Instance",
      exact: true,
    });
    await resource.waitFor();
    assert.equal(
      await resource.getByRole("heading", { name: "Create Compute Instance" })
        .evaluate((element) => element === document.activeElement),
      true,
    );
    await resource.getByRole("button", { name: "Close resource form" }).click();
    await resource.waitFor({ state: "hidden" });
    checks.push(
      `${mode}: execution drawer traps focus and closes with Escape; resource workspace receives focus and closes without saving`,
    );
    checks.push(
      `${mode}: eight primary destinations and administrator access screen show real backend evidence; status badges meet 4.5:1 contrast; investigation opens and Escape closes`,
    );
  }

  const sibling = await page.context().newPage();
  await sibling.goto(origin);
  await setTheme(sibling, "dark");
  await themeIs(page, "dark");
  await setTheme(sibling, "light");
  await themeIs(page, "light");
  await sibling.close();
  checks.push(
    "Appearance changes synchronize between documents through browser storage events",
  );

  await tab(page, "Overview");
  const sessionCheck = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/auth/me" &&
    response.request().method() === "GET",
  );
  await page.reload();
  const sessionStatus = (await sessionCheck).status();
  await themeIs(page, "light");
  if (sessionStatus === 200) {
    await page.getByRole("heading", { name: "Dashboard", exact: true }).waitFor();
  } else {
    assert.equal(sessionStatus, 401, "Only an expired session may require fresh authentication");
    await login(page);
    await chooseOrganization(page, "Controlled ETL Lab");
  }
  checks.push(
    "Explicit light preference survives document reload and authenticated session reconciliation",
  );
  const darkButton = page.getByRole("button", {
    name: "Dark theme",
    exact: true,
  });
  await darkButton.focus();
  await page.keyboard.press("Space");
  await themeIs(page, "dark");
  assert.equal(
    await darkButton.evaluate((element) => element === document.activeElement),
    true,
  );
  const lightButton = page.getByRole("button", {
    name: "Light theme",
    exact: true,
  });
  await lightButton.focus();
  await page.keyboard.press("Enter");
  await themeIs(page, "light");
  checks.push(
    "Theme buttons retain keyboard focus and support Space and Enter activation",
  );

  await page.setViewportSize({ width: 390, height: 844 });
  for (const mode of ["dark", "light"]) {
    await setTheme(page, mode);
    for (const name of [...primaryTabs, "Access Management"]) {
      await tab(page, name);
      await assertNoBodyOverflow(page, `${mode} ${name} at 390px`);
      if (name === "API Endpoint Monitoring")
        await screenshot(page, `${mode}-mobile-apis`);
    }
  }
  checks.push(
    "At 390px all nine screens remain accessible in both themes without body/document horizontal overflow",
  );

  await page.emulateMedia({ reducedMotion: "reduce" });
  await tab(page, "Overview");
  const motion = await page
    .locator(".unified-overview .card")
    .first()
    .evaluate((element) => ({
      reduced: matchMedia("(prefers-reduced-motion: reduce)").matches,
      transition: getComputedStyle(element).transitionDuration,
      animation: getComputedStyle(element).animationDuration,
    }));
  assert.equal(motion.reduced, true);
  for (const duration of [motion.transition, motion.animation]) {
    assert.ok(
      duration.split(",").every((value) => {
        const number = Number.parseFloat(value);
        return value.trim().endsWith("ms") ? number <= 1 : number <= 0.001;
      }),
      `Reduced motion must suppress KPI transitions and animations, received ${duration}`,
    );
  }
  checks.push(
    "Reduced-motion browser preference suppresses decorative card motion",
  );

  const systemLight = await makePage({ colorScheme: "light" });
  await systemLight.goto(origin);
  await themeIs(systemLight, "light");
  await systemLight.emulateMedia({ colorScheme: "dark" });
  await themeIs(systemLight, "dark");
  await setTheme(systemLight, "light");
  await systemLight.emulateMedia({ colorScheme: "light" });
  await systemLight.emulateMedia({ colorScheme: "dark" });
  await themeIs(systemLight, "light");
  checks.push(
    "Unset preference tracks operating-system theme changes; explicit selection stays selected",
  );

  const invalid = await makePage({ colorScheme: "light" }, () =>
    localStorage.setItem("opscontrol.theme", "invalid-theme"),
  );
  await invalid.goto(origin);
  await themeIs(invalid, "light");
  checks.push(
    "Invalid saved preference safely falls back to the browser light color scheme",
  );

  const storageDenied = await makePage({ colorScheme: "dark" }, () => {
    const denied = () => {
      throw new DOMException(
        "Synthetic browser storage denial",
        "SecurityError",
      );
    };
    Object.defineProperty(window.localStorage, "getItem", {
      configurable: true,
      value: denied,
    });
    Object.defineProperty(window.localStorage, "setItem", {
      configurable: true,
      value: denied,
    });
    Object.defineProperty(window.localStorage, "removeItem", {
      configurable: true,
      value: denied,
    });
  });
  await storageDenied.goto(origin);
  await themeIs(storageDenied, "dark");
  await setTheme(storageDenied, "light");
  await storageDenied
    .getByRole("textbox", { name: "Username", exact: true })
    .waitFor();
  checks.push(
    "Blocked localStorage preserves login rendering and in-memory appearance switching",
  );

  assert.deepEqual(pageErrors, [], "No browser JavaScript errors");
  assert.deepEqual(serverErrors, [], "No backend HTTP 5xx responses");
  await writeFile(
    join(output, "report.json"),
    JSON.stringify(
      {
        status: "PASS",
        browser: browser.version(),
        evidence:
          "Actual password authentication and fixture-backed APIs; no API mocks",
        primary_tabs: primaryTabs,
        administrator_tab: "Access Management",
        themes: ["dark", "light"],
        checks,
        screenshots,
        badge_text_contrast: contrast,
        page_errors: pageErrors,
        server_errors: serverErrors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(`PLAYWRIGHT UI TEST 1 PASS: ${checks.join("; ")}`);
} catch (error) {
  let index = 0;
  for (const context of browser.contexts())
    for (const page of context.pages()) {
      if (!page.isClosed())
        await page
          .screenshot({
            path: join(output, `failure-${index++}.png`),
            fullPage: true,
          })
          .catch(() => {});
    }
  await writeFile(
    join(output, "failure.json"),
    JSON.stringify(
      {
        status: "FAIL",
        error: error.message,
        checks,
        page_errors: pageErrors,
        server_errors: serverErrors,
      },
      null,
      2,
    ) + "\n",
  );
  throw error;
} finally {
  await browser.close();
}
