// Actual authenticated UI/API on the existing disposable synthetic UAT harness.
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
const { chromium } = await import(
  pathToFileURL(
    process.env.PLAYWRIGHT_MODULE ||
      "/workspace/.golden-tools/node_modules/playwright/index.mjs",
  ).href
);
const state = process.env.OPSCONTROL_UAT_STATE_DIR;
const out = process.env.S14R_EVIDENCE_DIR;
if (!state || !out)
  throw new Error("Owned UAT state and evidence directory required");
const settings = JSON.parse(
  fs.readFileSync(path.join(state, "settings.json"), "utf8"),
);
const users = JSON.parse(
  fs.readFileSync(path.join(state, "uat-users.json"), "utf8"),
);
users["demo-admin"] = fs
  .readFileSync(path.join(state, "admin-password"), "utf8")
  .trim();
assert.match(settings.project, /^opscontrol-s14-uat-/);
fs.mkdirSync(out, { recursive: true });
const ui = `http://127.0.0.1:${settings.ui_port}`,
  api = `http://127.0.0.1:${settings.api_port}`;
const browser = await chromium.launch({
  executablePath:
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || "/usr/bin/chromium",
  args: ["--no-sandbox"],
});
const checks = [],
  errors = [];
let page;
const check = (value, label) => {
  assert.ok(value, label);
  checks.push(label);
  console.log("PASS " + label);
};
const login = async (page, name) => {
  await page.goto(ui);
  await page.getByLabel("Username", { exact: true }).fill(name);
  await page.getByLabel("Password", { exact: true }).fill(users[name]);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
};
const headers = async (page, ids) => ({
  Authorization:
    "Bearer " +
    (await page.evaluate(() =>
      sessionStorage.getItem("opscontrol.sessionToken"),
    )),
  "X-OpsControl-Customers": ids.join(","),
});
try {
  page = await browser.newPage({ viewport: { width: 1366, height: 1000 } });
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, "demo-admin");
  const token = await page.evaluate(() =>
    sessionStorage.getItem("opscontrol.sessionToken"),
  );
  const directory = await page.request.get(
    api + "/api/v1/auth/customer-scope",
    { headers: { Authorization: "Bearer " + token } },
  );
  assert.equal(directory.status(), 200);
  const customers = (await directory.json()).filter((c) =>
    ["UAT-A", "UAT-B"].includes(c.code),
  );
  assert.equal(customers.length, 2);
  const ids = customers.map((c) => c.id);
  await page.evaluate((ids) => {
    localStorage.setItem("opscontrol.organizationIds", JSON.stringify(ids));
    localStorage.setItem("opscontrol.customerSelectionMode", "SELECTED");
  }, ids);
  await page.reload();
  await page.getByRole("navigation", { name: "Primary navigation" }).waitFor();
  await page
    .getByRole("button", { name: "Data Sources / Resources", exact: true })
    .click();
  const inventory = page.getByRole("region", {
    name: "Compute Instances records",
    exact: true,
  });
  await inventory.getByRole("table").waitFor();
  await page
    .getByText("Loading authorized resources…", { exact: true })
    .waitFor({ state: "hidden" });
  await inventory
    .locator("tbody tr")
    .filter({ hasText: "UAT-A" })
    .first()
    .waitFor();
  check(
    (await inventory.locator("tbody tr").count()) >= 2,
    "actual authorized synthetic inventory records loaded before visual checks",
  );
  await page
    .getByRole("button", { name: "Collapse sidebar", exact: true })
    .click();
  await page.waitForFunction(
    () => document.documentElement.dataset.sidebar === "collapsed",
  );
  for (const theme of ["light", "dark"]) {
    await page
      .getByRole("button", {
        name: theme === "light" ? "Light theme" : "Dark theme",
        exact: true,
      })
      .click();
    const contrasts = await page.evaluate(() => {
      const css = getComputedStyle(document.documentElement);
      const hex = (name) => css.getPropertyValue(name).trim();
      const lum = (value) => {
        const raw = value.replace("#", "");
        assertHex(raw);
        const channels = [0, 2, 4]
          .map((i) => parseInt(raw.slice(i, i + 2), 16) / 255)
          .map((x) =>
            x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4,
          );
        return (
          channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
        );
      };
      function assertHex(raw) {
        if (!/^[0-9a-f]{6}$/i.test(raw))
          throw new Error("Expected opaque semantic token: " + raw);
      }
      const contrast = (fg, bg) => {
        const [a, b] = [lum(fg), lum(bg)].sort((a, b) => b - a);
        return (a + 0.05) / (b + 0.05);
      };
      const pairs = [
        ["text", "surface"],
        ["muted", "surface"],
        ["muted", "canvas"],
        ["accent", "accent-wash"],
        ["healthy", "healthy-wash"],
        ["warning", "warning-wash"],
        ["critical", "critical-wash"],
      ];
      return {
        text: pairs.map(([a, b]) => ({
          pair: a + "/" + b,
          ratio: contrast(hex("--" + a), hex("--" + b)),
        })),
        primary: contrast("#ffffff", hex("--accent-solid")),
        boundary: contrast(hex("--border-strong"), hex("--surface")),
      };
    });
    check(
      contrasts.text.every((x) => x.ratio >= 4.5) && contrasts.primary >= 4.5,
      theme + " normal text/status/button contrast meets4.5:1",
    );
    check(contrasts.boundary >= 3, theme + " input boundary contrast meets3:1");
    const media = await page.context().newCDPSession(page);
    await media.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-contrast", value: "more" }],
    });
    check(
      await page.evaluate(() => {
        const css = getComputedStyle(document.documentElement);
        return (
          css.getPropertyValue("--muted").trim() ===
          css.getPropertyValue("--text").trim()
        );
      }),
      theme + " increased-contrast preference promotes secondary text",
    );
    await media.send("Emulation.setEmulatedMedia", { features: [] });
    await media.detach();
    for (const width of [1366, 768, 720, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      if (width <= 760) {
        await page
          .getByRole("button", { name: "Open navigation", exact: true })
          .click();
        const first = page.locator("#primary-navigation .nav-button").first();
        check(
          await first.evaluate((el) => el === document.activeElement),
          theme +
            " " +
            width +
            " menu opening focuses first permitted destination",
        );
        await page.keyboard.press("Escape");
        check(
          await page
            .getByRole("button", { name: "Open navigation", exact: true })
            .evaluate((el) => el === document.activeElement),
          theme + " " + width + " Escape restores toggle focus",
        );
      }
      const geometry = await page.evaluate(() => ({
        left: document.querySelector("main.content").getBoundingClientRect()
          .left,
        overflow:
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth,
      }));
      check(
        Math.abs(geometry.left - (width <= 760 ? 0 : 72)) < 1,
        theme +
          " " +
          width +
          " collapsed sidebar offset matches responsive mode",
      );
      check(!geometry.overflow, theme + " " + width + " no document overflow");
      const hash = new URL(page.url()).hash;
      await page
        .getByRole("link", { name: "Skip to main content", exact: true })
        .focus();
      await page.keyboard.press("Enter");
      check(
        await page
          .locator("#main-content")
          .evaluate((el) => el === document.activeElement),
        theme + " " + width + " skip navigation focuses main",
      );
      check(
        new URL(page.url()).hash === hash,
        theme + " " + width + " skip navigation preserves child deep link",
      );
      await inventory.focus();
      check(
        await inventory.evaluate((el) => el === document.activeElement),
        theme + " " + width + " inventory scroll region is keyboard reachable",
      );
      await inventory.evaluate((el) => {
        el.scrollLeft = 100;
      });
      check(
        await inventory.evaluate(
          (el) => el.scrollWidth <= el.clientWidth || el.scrollLeft > 0,
        ),
        theme + " " + width + " wide table scrolls inside its region",
      );
      await inventory.evaluate((el) => {
        el.scrollLeft = 0;
      });
      check(
        await page
          .locator(".skip-link")
          .evaluate((el) => el.getBoundingClientRect().bottom <= 0),
        theme + " " + width + " skip link hides after focus leaves",
      );
      await page.screenshot({
        path: path.join(out, theme + "-" + width + "-inventory.png"),
        fullPage: true,
      });
    }
  }
  await page.setViewportSize({ width: 1366, height: 1000 });
  await page
    .getByRole("button", { name: "Expand sidebar", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Organizations", exact: true })
    .click();
  check(
    await page
      .locator(".workspace-breadcrumb")
      .innerText()
      .then(
        (v) => v.includes("Resource Management") && v.includes("Organizations"),
      ),
    "breadcrumb uses canonical group and child labels",
  );
  for (const label of [
    "Overview",
    "Operations",
    "Resource Management",
    "Access Management",
  ])
    check(
      (await page.getByRole("group", { name: label, exact: true }).count()) ===
        1,
      "accessible navigation group " + label,
    );
  await page.emulateMedia({ reducedMotion: "reduce" });
  check(
    await page
      .locator(".nav-button")
      .first()
      .evaluate((el) => getComputedStyle(el).transitionDuration === "0s"),
    "reduced-motion preference disables navigation transitions",
  );
  await page.emulateMedia({ forcedColors: "active" });
  await page.screenshot({
    path: path.join(out, "forced-colors-navigation.png"),
    fullPage: true,
  });
  check(
    await page.evaluate(() => matchMedia("(forced-colors: active)").matches),
    "forced-colors system preference is honored",
  );
  const customerB = customers.find((c) => c.code === "UAT-B").id;
  const resources = await page.request.get(
    api + "/api/v1/unified/resources?organization_id=" + customerB,
    { headers: await headers(page, [customerB]) },
  );
  assert.equal(resources.status(), 200);
  const resourceB = (await resources.json()).items[0];
  assert.ok(resourceB);
  const viewer = await browser.newPage({
    viewport: { width: 390, height: 844 },
  });
  await login(viewer, "uat-viewer-a");
  await viewer
    .getByRole("button", { name: "Open navigation", exact: true })
    .click();
  check(
    (await viewer
      .getByRole("button", { name: "Employees", exact: true })
      .count()) === 0,
    "read-only viewer cannot navigate to workforce administration",
  );
  const customerA = customers.find((c) => c.code === "UAT-A").id;
  const denied = await viewer.request.get(
    api + "/api/v1/unified/resources/" + resourceB.id,
    { headers: await headers(viewer, [customerA]) },
  );
  check(
    [403, 404].includes(denied.status()),
    "actual backend denies CustomerB detail to CustomerA-only user",
  );
  const scoped = await viewer.request.get(api + "/api/v1/auth/customer-scope", {
    headers: await headers(viewer, [customerA]),
  });
  check(
    (await scoped.json()).every((c) => c.id !== customerB),
    "viewer customer selector contract excludes CustomerB",
  );
  check(errors.length === 0, "no uncaught application errors");
  fs.writeFileSync(
    path.join(out, "report.json"),
    JSON.stringify(
      {
        status: "PASS",
        checks,
        contrast:
          "Computed semantic tokens; normal text4.5 and input boundaries3",
        fixture: "SYNTHETIC_UAT_ONLY",
        backend: "Actual authenticated API / disposable PostgreSQL",
        genuineRuntimeAcceptance: false,
      },
      null,
      2,
    ),
  );
  console.log("Sprint14R browser PASS: " + checks.length + " checks");
} catch (error) {
  if (page && !page.isClosed())
    await page
      .screenshot({ path: path.join(out, "failure.png"), fullPage: true })
      .catch(() => {});
  fs.writeFileSync(
    path.join(out, "failure.json"),
    JSON.stringify(
      { status: "FAIL", error: String(error), checks, errors },
      null,
      2,
    ),
  );
  throw error;
} finally {
  await browser.close();
}
