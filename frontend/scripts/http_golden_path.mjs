// Actual browser assertions/screenshots; no injected sessions or mocked HTTP.
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE).href : 'playwright');
const state=JSON.parse(await readFile(process.env.GOLDEN_SESSION_FILE,'utf8'));
const phase=process.argv[2];
const output=process.env.GOLDEN_EVIDENCE_DIR;
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {})});
const errors=[];
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(process.env.GOLDEN_UI_URL||'http://127.0.0.1:15173');
  await page.getByRole('textbox',{name:'Username'}).fill(state.operator_username);
  await page.getByLabel('Password').fill(state.operator_password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await page.getByRole('button',{name:'Resource Management',exact:true}).click();
  await page.getByRole('tab',{name:'API Endpoints',exact:true}).click();
  await page.getByRole('button',{name:'Fictional HTTPS Portal',exact:true}).click();
  await page.getByRole('button',{name:'Open legacy monitoring configuration',exact:true}).click();
  assert.equal(await page.getByLabel(/^Data Source/).inputValue(), state.source_id);
  assert.equal(await page.getByLabel(/^Data Source/).isDisabled(), true);
  const diag=page.getByTestId('monitoring-diagnostics');
  await diag.locator('p').filter({hasText:/Activation: ACTIVE/}).waitFor();
  if(phase==='configured') {
    for(const name of ['golden-readiness','golden-http-events','golden-unavailable']) {
      const row=page.locator('.monitoring-rule-option').filter({hasText:name}).filter({hasText:'Version 1'});
      await row.getByRole('checkbox').check();
    }
    await page.getByRole('button',{name:'Validate & Preview',exact:true}).click();
    await page.getByText('Activation preview validated; no collector changed.',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Activate monitoring',exact:true}).click();
    await page.getByText('Configuration already active — no duplicate collector created.',{exact:true}).waitFor();
    await diag.getByText('0 metric samples · 0 open alerts · 0 resolved alerts',{exact:false}).waitFor();
    await diag.getByText('NO_EVIDENCE',{exact:false}).first().waitFor();
  } else {
    const expected={healthy:[1,0,0,200],failed:[2,1,0,503],recovered:[3,0,1,200]}[phase];
    assert(expected,'Unknown phase');
    const [count,open,resolved,status]=expected;
    await diag.getByText(`${count} metric samples · ${open} open alerts · ${resolved} resolved alerts`,{exact:false}).waitFor();
    await diag.getByText(`HTTP ${status}`,{exact:false}).waitFor();
    await diag.getByText('freshness CURRENT',{exact:false}).waitFor();
    await diag.getByText('COMPLETED',{exact:false}).first().waitFor();
  }
  await page.screenshot({path:`${output}/${phase}.png`,fullPage:true});
  if(phase==='recovered') {
    const other=await browser.newPage({viewport:{width:1440,height:1000}});
    other.on('pageerror',error=>errors.push(error.message));
    await other.goto(process.env.GOLDEN_UI_URL||'http://127.0.0.1:15173');
    await other.getByRole('textbox',{name:'Username'}).fill(state.other_username);
    await other.getByLabel('Password').fill(state.other_password);
    await other.getByRole('button',{name:'Sign in'}).click();
    await other.getByRole('button',{name:'Resource Management',exact:true}).click();
    await other.getByRole('tab',{name:'API Endpoints',exact:true}).click();
    await other.getByText('No resources match these authorized filters.',{exact:true}).waitFor();
    assert.equal(await other.getByRole('button',{name:'Fictional HTTPS Portal',exact:true}).count(),0);
    assert.equal(await other.getByLabel(/^Data Source/).count(),0);
    await other.screenshot({path:`${output}/other-tenant.png`,fullPage:true});
  }
  assert.deepEqual(errors,[]);
  console.log(`PLAYWRIGHT ${phase}: authenticated UI, diagnostics and screenshot PASS`);
} finally { await browser.close(); }
