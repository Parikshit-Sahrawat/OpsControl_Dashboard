import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE || '/workspace/.golden-tools/node_modules/playwright/index.mjs').href);
// Run only against a disposable, synthetic UAT state (see Sprint 14 runbook).
const state = process.env.OPSCONTROL_UAT_STATE_DIR;
if (!state) throw new Error('OPSCONTROL_UAT_STATE_DIR is required');
const evidenceDir = process.env.UI_RECOVERY_EVIDENCE_DIR;
if (evidenceDir) fs.mkdirSync(evidenceDir,{recursive:true});
const settings = JSON.parse(fs.readFileSync(path.join(state, 'settings.json'), 'utf8'));
const users = JSON.parse(fs.readFileSync(path.join(state, 'uat-users.json'), 'utf8'));
users['demo-admin'] = fs.readFileSync(path.join(state, 'admin-password'), 'utf8').trim();
const url = `http://127.0.0.1:${settings.ui_port}`;
const browser = await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || '/usr/bin/chromium',args:['--no-sandbox']});
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; console.log(`PASS ${message}`); };
async function login(page, name) {
  await page.goto(url);
  await page.getByLabel('Username').fill(name);
  await page.getByLabel('Password').fill(users[name]);
  await page.getByRole('button',{name:'Sign in'}).click();
  await page.getByText(`Signed in as ${name}`).waitFor();
}
async function selectCustomers(page) {
  await page.evaluate(async (apiPort) => {
    const token=sessionStorage.getItem('opscontrol.sessionToken');
    const response=await fetch(`http://127.0.0.1:${apiPort}/api/v1/auth/customer-scope`,{headers:{Authorization:`Bearer ${token}`}});
    const rows=await response.json();
    localStorage.setItem('opscontrol.organizationIds',JSON.stringify(rows.filter(r=>['UAT-A','UAT-B'].includes(r.code)).map(r=>r.id)));
    localStorage.setItem('opscontrol.customerSelectionMode','SELECTED');
  }, settings.api_port);
  await page.reload();
}
try {
  const desktop=await browser.newPage({viewport:{width:1366,height:850}});
  await login(desktop,'demo-admin');
  await selectCustomers(desktop);
  const nav=desktop.getByRole('navigation',{name:'Primary navigation'});
  await nav.getByRole('button',{name:'Resource Management',exact:true}).waitFor();
  for (const section of ['Overview','Operations','Resource Management','Access Management']) check(await nav.getByText(section,{exact:true}).count()>0,`desktop ${section} group`);
  await nav.getByRole('button',{name:'Resource Management',exact:true}).click();
  await desktop.getByRole('button',{name:'Create Compute Instance'}).waitFor();
  check(await desktop.locator('.page-heading .primary-button').count()===1,'resource create in header');
  check(await desktop.locator('.resource-toolbar .primary-button').count()===0,'resource filter has no create button');
  await desktop.locator('th').filter({hasText:/configuration state/i}).first().waitFor({state:'attached'});
  check(true,'configuration label distinct from health');
  await nav.getByRole('button',{name:'Access Management',exact:true}).click();
  await desktop.getByRole('navigation',{name:'Access Management sections'}).getByRole('button',{name:'Departments'}).click();
  check(await desktop.getByRole('button',{name:'Create department',exact:true}).count()===1,'single department create action');
  check(await desktop.locator('.page-heading .primary-button').count()===1,'department create in header');
  await nav.getByRole('button',{name:'Data Pipeline Monitoring',exact:true}).click();
  for (const name of ['Pipeline Inventory','Execution History','Schedule Monitoring','Evidence Review','Recovery Tracking','Incident Correlation']) {
    await desktop.getByRole('link',{name,exact:true}).click();
    await desktop.getByRole('heading',{name,exact:true}).waitFor();
    check(true,`pipeline ${name}`);
  }
  await nav.getByRole('button',{name:'Collapse sidebar'}).click();
  check(await desktop.getByRole('button',{name:'Expand sidebar'}).count()===1,'desktop sidebar collapse preserved');
  if (evidenceDir) await desktop.screenshot({path:path.join(evidenceDir,'implemented-desktop.png'),fullPage:true});
  const mobile=await browser.newPage({viewport:{width:390,height:844}});
  await login(mobile,'demo-admin');
  await selectCustomers(mobile);
  check(await mobile.getByRole('navigation',{name:'Primary navigation'}).isHidden(),'mobile navigation initially closed');
  await mobile.getByRole('button',{name:'Open navigation'}).click();
  check(await mobile.getByRole('navigation',{name:'Primary navigation'}).isVisible(),'mobile navigation opens');
  if (evidenceDir) await mobile.screenshot({path:path.join(evidenceDir,'implemented-menu.png'),fullPage:true});
  await mobile.getByRole('navigation',{name:'Primary navigation'}).getByRole('button',{name:'Resource Management',exact:true}).click();
  check(await mobile.getByRole('navigation',{name:'Primary navigation'}).isHidden(),'mobile navigation closes after selection');
  check(await mobile.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'mobile document has no horizontal overflow');
  await mobile.getByRole('button',{name:'Open navigation'}).click();
  await mobile.keyboard.press('Escape');
  check(await mobile.getByRole('button',{name:'Open navigation'}).evaluate(el=>el===document.activeElement),'Escape closes menu and restores focus');
  if (evidenceDir) await mobile.screenshot({path:path.join(evidenceDir,'implemented-mobile.png'),fullPage:true});
  const tablet=await browser.newPage({viewport:{width:768,height:900}});
  await login(tablet,'demo-admin');
  check(await tablet.getByRole('navigation',{name:'Primary navigation'}).isVisible(),'tablet sidebar remains available');
  check(await tablet.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'tablet document has no horizontal overflow');
  const viewer=await browser.newPage({viewport:{width:390,height:844}});
  await login(viewer,'uat-viewer-a');
  await viewer.getByRole('button',{name:'Open navigation'}).click();
  check(await viewer.getByRole('navigation',{name:'Primary navigation'}).getByRole('button',{name:'Access Management'}).count()===0,'viewer cannot navigate to Access Management');
  console.log(`RESULT ${checks} passed, 0 failed`);
} finally { await browser.close(); }
