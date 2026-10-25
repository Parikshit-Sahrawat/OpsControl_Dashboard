import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const s=JSON.parse(await readFile(process.env.GOLDEN_SESSION_FILE,'utf8'));
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const report={};
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(15000);
  await page.goto(process.env.GOLDEN_UI_URL);
  await page.getByLabel('Username').fill(s.operator_username);
  await page.getByLabel('Password').fill(s.operator_password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.locator('.org-context-button').click();
  await page.locator('.org-option').filter({hasText:'Golden HTTP Lab'}).getByRole('checkbox').check();
  async function open(){
    await page.getByRole('button',{name:'Data Sources / Resources',exact:true}).click();
    await page.getByRole('tab',{name:'API Endpoints',exact:true}).click();
    await page.getByRole('button',{name:'Fictional HTTPS Portal',exact:true}).click();
    await page.getByRole('button',{name:'Open legacy monitoring configuration',exact:true}).click();
    await page.waitForFunction(expected=>[...document.querySelectorAll('select')].some(x=>x.disabled&&x.value===expected),s.source_id);
  }
  await open();
  for (const name of ['golden-readiness','golden-http-events','golden-unavailable'])
    await page.locator('.monitoring-rule-option').filter({hasText:name}).filter({hasText:'Version 1'}).getByRole('checkbox').check();
  await page.getByLabel(/^HTTP method/).selectOption('HEAD');
  await page.getByLabel('Maximum response time (ms, optional)',{exact:true}).fill('10000');
  await page.getByLabel('Approved x-opscontrol-check header (optional)',{exact:true}).fill('dev05-ui');
  await page.getByRole('button',{name:'Validate & Preview',exact:true}).click();
  await page.getByText('Activation preview validated; no collector changed.',{exact:true}).waitFor();
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/activations')&&r.request().method()==='POST');
  await page.locator('.monitoring-setup').getByRole('button',{name:'Activate monitoring',exact:true}).click();
  const response=await responsePromise;
  assert.equal(response.status(),200);
  report.saved=true;
  await page.reload(); await open();
  report.reloadedMethod=await page.getByLabel(/^HTTP method/).inputValue();
  report.reloadedLatency=await page.getByLabel('Maximum response time (ms, optional)',{exact:true}).inputValue();
  report.reloadedHeader=await page.getByLabel('Approved x-opscontrol-check header (optional)',{exact:true}).inputValue();
  await page.screenshot({path:process.env.GOLDEN_EVIDENCE_DIR+'/saved-api-settings.png',fullPage:true});
  assert.equal(report.reloadedMethod,'HEAD','Saved method must rehydrate after reload');
  assert.equal(report.reloadedLatency,'10000','Saved latency must rehydrate after reload');
  assert.equal(report.reloadedHeader,'dev05-ui','Saved approved header must rehydrate after reload');
} finally {
  await writeFile(process.env.GOLDEN_EVIDENCE_DIR+'/saved-api-settings.json',JSON.stringify(report,null,2)+'\n');
  await browser.close();
}
