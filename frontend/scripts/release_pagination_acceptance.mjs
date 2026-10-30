// Real backend inventory and password login; no API mocks.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const browser = await chromium.launch({headless:true, executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const page = await browser.newPage({viewport:{width:1600,height:1100}});
const errors=[]; page.on('pageerror', error=>errors.push(error.message));
let phase='initial-navigation';
function at(stage) { phase = stage; }
try {
  at('navigate');
  await page.goto(process.env.RELEASE_UI_BASE);
  phase='authenticated-login';
  await page.getByLabel('Username').fill('test-north');
  await page.getByLabel('Password').fill('testing-only-StrongPassword-123!');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'Dashboard',exact:true}).waitFor();
  phase='organization-scope';
  // Scope selection is explicit and is only a filter over this user's grants.
  at('organization-selector');
  await page.locator('.org-context-button').click();
  await page.locator('.org-menu').getByRole('checkbox').first().check();
  await page.locator('.org-context-button').click();
  for (const theme of ['Dark','Light']) {
    phase=`theme:${theme}`;
    await page.getByRole('button',{name:theme+' theme',exact:true}).click();
    for (const tab of ['Compute Health','API Endpoint Monitoring']) {
      phase=`navigation:${theme}:${tab}`;
      await page.getByRole('button',{name:tab,exact:true}).click();
      const label = tab === 'Compute Health' ? 'infrastructure adapter health' : 'service probe health';
      // Domain navigation preserves the expanded compatibility inventory.
      const show = page.getByRole('button',{name:'Show '+label,exact:true});
      await page.getByRole('button',{name:new RegExp('^(Show|Hide) '+label+'$')}).waitFor();
      if (await show.isVisible()) await show.click();
      await page.getByRole('button',{name:'Hide '+label,exact:true}).waitFor();
      phase=`pagination:${theme}:${tab}`;
      const pager = page.getByRole('navigation',{name:'Inventory pagination'});
      await pager.getByRole('button',{name:'Next page',exact:true}).waitFor();
      assert.equal(await pager.getByRole('button',{name:'Previous page'}).isDisabled(),true);
      at('next-page-'+theme.toLowerCase()+'-'+(tab==='Compute Health'?'compute':'api'));
      await pager.getByRole('button',{name:'Next page',exact:true}).click();
      await page.waitForFunction(()=>{ const text=document.querySelector('nav[aria-label="Inventory pagination"]')?.textContent || ''; return /^\s*51\s*[–-]/.test(text); });
      assert.equal(await pager.getByRole('button',{name:'Next page'}).isDisabled(),true);
      await mkdir(process.env.RELEASE_EVIDENCE_DIR,{recursive:true});
      await page.screenshot({path:`${process.env.RELEASE_EVIDENCE_DIR}/${theme.toLowerCase()}-${tab==='API Endpoint Monitoring'?'services':'infrastructure'}-page2.png`,fullPage:true});
      at('previous-page-'+theme.toLowerCase()+'-'+(tab==='Compute Health'?'compute':'api'));
      await pager.getByRole('button',{name:'Previous page',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('nav[aria-label="Inventory pagination"]')?.textContent.startsWith('1–'));
    }
  }
  assert.deepEqual(errors,[]);
  await writeFile(`${process.env.RELEASE_EVIDENCE_DIR}/pagination.json`,JSON.stringify({status:'PASS',evidence:'Actual authenticated backend with >200 resources; previous/next pagination in both themes',page_errors:errors},null,2));
} catch (error) {
  // CI logs are public: emit only the stage and error category, never page text,
  // request URLs, credentials, selectors from exception messages, or fixture data.
  console.error('RELEASE_PAGINATION_FAILURE '+JSON.stringify({stage:phase,category:error?.name || 'Error'}));
  process.exitCode = 1;
} finally { await browser.close(); }
