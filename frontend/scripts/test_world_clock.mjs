import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on("pageerror", error => errors.push(String(error)));
try {
  await page.goto("http://127.0.0.1:5173", { waitUntil: "domcontentloaded" });
  const clock = page.locator(".world-clock");
  await clock.waitFor();
  const selector = page.getByRole("combobox", { name: "World clock timezone" });
  if (await selector.inputValue() !== "Asia/Kolkata") throw new Error("Unexpected default timezone");
  const before = await clock.locator("time").innerText();
  await page.waitForTimeout(1350);
  const after = await clock.locator("time").innerText();
  if (before === after) throw new Error("Clock did not tick independently");
  await selector.selectOption("America/New_York");
  const ny = await clock.locator("time").innerText();
  if (ny === after) throw new Error("Changing timezone did not change displayed time");
  if (!/New York/.test(await selector.locator("option:checked").innerText())) throw new Error("Timezone selection lost");
  await page.reload();
  if (await selector.inputValue() !== "America/New_York") throw new Error("Timezone preference not preserved across reload");
  await selector.selectOption("UTC");
  const utc = await clock.locator("time").innerText();
  const expected = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).format(new Date());
  if (utc.slice(0, 5) !== expected.slice(0, 5)) throw new Error(`UTC clock inconsistent: ${utc} vs ${expected}`);
  if (errors.length) throw new Error(errors.join("; "));
  console.log(JSON.stringify({ status: "PASS", ticked: true, selectedZone: "UTC", preferencePersisted: true, display: utc }));
} finally {
  await browser.close();
}
