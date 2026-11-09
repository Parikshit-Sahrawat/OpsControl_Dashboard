// Real browser/native HTTP regression for the acceptance-only delivery gate.
import test, { before, after } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { pathToFileURL } from "node:url";
import { holdBrowserResponses } from "./browser_response_gate.mjs";

let browser, server, site, base, ui;
const receipts = [];
before(async () => {
  const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
  browser = await chromium.launch({headless:true, executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
  site = http.createServer((_req,res) => res.end("<!doctype html><title>Owned fetch fixture</title>"));
  await new Promise(resolve => site.listen(0,"127.0.0.1",resolve));
  ui = `http://127.0.0.1:${site.address().port}`;
  server = http.createServer((req,res) => {
    if (req.url.startsWith("/network-failure")) { req.socket.destroy(); return; }
    if (!req.url.startsWith("/cors-denied")) {
      res.setHeader("Access-Control-Allow-Origin",ui);
      res.setHeader("Access-Control-Allow-Headers","Content-Type,X-Test-Nonce");
    }
    if (req.method === "OPTIONS") { res.end(); return; }
    const id = receipts.length;
    receipts.push({id,method:req.method,nonce:req.headers["x-test-nonce"] || null});
    res.statusCode = req.url.includes("forbidden") ? 403 : 200;
    res.setHeader("Content-Type","application/json");
    res.end(JSON.stringify(receipts[id]));
  });
  await new Promise(resolve => server.listen(0,"127.0.0.1",resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(async () => {
  await browser?.close();
  for (const fixture of [site,server]) if (fixture) await new Promise(resolve => fixture.close(resolve));
});
async function fixture(t) {
  const page = await browser.newPage();
  t.after(() => page.close());
  await page.goto(ui);
  return page;
}

test("two genuine cross-origin responses stay held while unrelated requests and headers remain native",async t => {
  const page = await fixture(t);
  const gate = await holdBrowserResponses(page,"/configuration-context");
  const start = receipts.length;
  await page.evaluate(base => {
    window.delivered = [];
    window.waiting = ["first","second"].map(nonce => fetch(base+"/configuration-context",{headers:{"Content-Type":"application/json","X-Test-Nonce":nonce}}).then(r=>r.json()).then(value=>window.delivered.push(value)));
  },base);
  await page.waitForFunction(() => window.__opscontrolResponseGate.state.pending === 2);
  assert.equal(receipts.length-start,2);
  assert.deepEqual(receipts.slice(start).map(x=>x.nonce).sort(),["first","second"]);
  assert.deepEqual(await page.evaluate(()=>window.delivered),[]);
  const post = await page.evaluate(async base => (await fetch(base+"/configuration-context",{method:"POST",headers:{"X-Test-Nonce":"post"}})).json(),base);
  assert.equal(post.method,"POST");
  const state = await gate.release();
  assert.equal(state.pending,0);
  assert.equal(state.completed,2);
  await page.evaluate(()=>Promise.all(window.waiting));
  assert.deepEqual(await page.evaluate(()=>window.delivered.map(x=>x.id).sort()),receipts.slice(start,start+2).map(x=>x.id).sort());
});

test("repeated gates and idempotent release preserve forbidden status and restore native fetch",async t => {
  const page = await fixture(t);
  await page.evaluate(()=>{window.nativeFetch=window.fetch;});
  for (let i=0;i<10;i++) {
    const gate = await holdBrowserResponses(page,"/configuration-context");
    await page.evaluate(base=>{window.result=fetch(base+"/forbidden/configuration-context").then(async r=>({status:r.status,body:await r.json()}));},base);
    await page.waitForFunction(()=>window.__opscontrolResponseGate.state.pending===1);
    await gate.release();
    assert.equal((await gate.release()).completed,1);
    const actual = await page.evaluate(()=>window.result);
    assert.equal(actual.status,403);
    assert.equal(actual.body.method,"GET");
    assert.equal(await page.evaluate(()=>window.fetch===window.nativeFetch),true);
    assert.equal(await page.evaluate(async base=>(await fetch(base+"/configuration-context")).status,base),200);
  }
});

test("native CORS denial and transport failure propagate without fabricated responses",async t => {
  const page = await fixture(t);
  const gate = await holdBrowserResponses(page,"/configuration-context");
  for (const prefix of ["cors-denied","network-failure"]) {
    const error = await page.evaluate(async ({base,prefix})=>{
      try { await fetch(base+"/"+prefix+"/configuration-context"); return "incorrect success"; }
      catch(error) { return error.name; }
    },{base,prefix});
    assert.equal(error,"TypeError");
  }
  assert.equal((await gate.release()).received,0);
});
