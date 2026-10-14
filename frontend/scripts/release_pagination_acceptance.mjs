// Real backend inventory and password login; no API mocks.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const browser = await chromium.launch({headless:true, executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const page = await browser.newPage({viewport:{width:1600,height:1100}});
const errors=[]; page.on('pageerror', error=>errors.push(error.message));
try {
  await page.goto(process.env.RELEASE_UI_BASE);
  await page.getByLabel('Username').fill('test-north');
  await page.getByLabel('Password').fill('testing-only-StrongPassword-123!');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'Overview',exact:true}).waitFor();
  for (const theme of ['Dark','Light']) {
    await page.getByRole('button',{name:theme+' theme',exact:true}).click();
    for (const tab of ['VM Health','APIs']) {
      await page.getByRole('button',{name:tab,exact:true}).click();
      const pager = page.getByRole('navigation',{name:'Inventory pagination'});
      await pager.getByRole('button',{name:'Next page',exact:true}).waitFor();
      assert.equal(await pager.getByRole('button',{name:'Previous page'}).isDisabled(),true);
      await pager.getByRole('button',{name:'Next page',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('nav[aria-label="Inventory pagination"]')?.textContent.startsWith('201–'));
      assert.equal(await pager.getByRole('button',{name:'Next page'}).isDisabled(),true);
      await mkdir(process.env.RELEASE_EVIDENCE_DIR,{recursive:true});
      await page.screenshot({path:`${process.env.RELEASE_EVIDENCE_DIR}/${theme.toLowerCase()}-${tab==='APIs'?'services':'infrastructure'}-page2.png`,fullPage:true});
      await pager.getByRole('button',{name:'Previous page',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('nav[aria-label="Inventory pagination"]')?.textContent.startsWith('1–'));
    }
  }
  assert.deepEqual(errors,[]);
  await writeFile(`${process.env.RELEASE_EVIDENCE_DIR}/pagination.json`,JSON.stringify({status:'PASS',evidence:'Actual authenticated backend with >200 resources; previous/next pagination in both themes',page_errors:errors},null,2));
} finally { await browser.close(); }
