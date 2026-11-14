import { checkFoundation } from "./aptron_foundation_acceptance.mjs";
// Controlled, authenticated scope rejection. No synthetic operational status.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE));
const fixture=JSON.parse(await readFile(join(process.env.V16_PRIVATE_DIR,'browser-fixture.json'),'utf8'));
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? {executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
const page=await browser.newPage({viewport:{width:1440,height:900}});
const result={status:'NOT_RUN',checks:[],scope:'Authenticated UI scope exclusion; not owner UAT or provider qualification'};
try {
  await page.goto(process.env.V16_UI_URL);
  await page.getByLabel('Username',{exact:true}).fill('v16-api-admin');
  await page.getByLabel('Password',{exact:true}).fill(fixture.password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  const nav=page.getByRole('navigation',{name:'Primary navigation'});
  await nav.waitFor();
  const count=await nav.getByRole('button',{name:'Incidents',exact:true}).count();
  result.checks.push({id:'excluded-incident-navigation',expected:0,actual:count,status:count===0?'PASS':'FAIL'});
  await page.screenshot({path:join(process.env.V16_EVIDENCE_DIR,'ci-scope-desktop.png'),fullPage:true});
  assert.equal(count,0,'Excluded incident-management UI must not be offered as supported');
  await checkFoundation(page,fixture,process.env.V16_EVIDENCE_DIR);
  result.status='PASS';
} catch(error) {
  result.status='FAIL';result.error=error.message;
  await page.screenshot({path:join(process.env.V16_EVIDENCE_DIR,'ci-scope-failed.png'),fullPage:true});
  throw error;
} finally {
  await writeFile(join(process.env.V16_EVIDENCE_DIR,'ci-scope.json'),JSON.stringify(result,null,2));
  await browser.close();
}
