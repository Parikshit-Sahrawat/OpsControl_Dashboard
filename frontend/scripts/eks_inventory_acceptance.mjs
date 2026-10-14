// Actual imported EKS fixture inventory; no browser API mocks.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const page=await browser.newPage({viewport:{width:1600,height:1100}});
const errors=[], serverErrors=[], collectorUrls=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('response',r=>{if(r.url().includes('/api/')&&r.status()>=500)serverErrors.push(r.status());});
page.on('request',r=>{if(r.url().includes('/api/v1/resource-management/collectors?'))collectorUrls.push(r.url());});
try {
  await page.goto(process.env.RELEASE_UI_BASE);
  await page.getByLabel('Username').fill('test-north');
  await page.getByLabel('Password').fill('testing-only-StrongPassword-123!');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'Overview',exact:true}).waitFor();
  await page.getByRole('button',{name:'Resource Management',exact:true}).click();
  await page.locator('.resource-summary-card').filter({hasText:'Data Sources'}).click();
  await page.locator('.resource-toolbar input').fill('aws:123456789012:ap-south-1:eks:sequence-eks');
  const row=page.getByRole('row').filter({hasText:'sequence-eks'});
  await row.waitFor();
  await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(b=>b.textContent==='Refresh'&&!b.disabled));
  assert.equal(await row.getByRole('button',{name:'Edit',exact:true}).isDisabled(),true);
  assert.match(await row.textContent(),/DISCOVERY ONLY/);
  await mkdir(process.env.RELEASE_EVIDENCE_DIR,{recursive:true});
  for(const theme of ['Dark','Light']) {
    await page.getByRole('button',{name:theme+' theme',exact:true}).click();
    await page.screenshot({path:process.env.RELEASE_EVIDENCE_DIR+'/eks-'+theme.toLowerCase()+'.png',fullPage:true});
  }
  assert.ok(collectorUrls.length>=2);
  assert.ok(collectorUrls.every(url=>url.length<4096),'Collector request exceeds ingress request-line budget');
  assert.deepEqual(errors,[]); assert.deepEqual(serverErrors,[]);
  await writeFile(process.env.RELEASE_EVIDENCE_DIR+'/eks-browser.json',JSON.stringify({status:'PASS',
    checks:['Real imported EKS resource shown in both themes','Discovery-only inventory has no enabled agent or generic machine editor',
            'Large resource inventory uses bounded collector query batches below 4 KiB'],
    collector_requests:collectorUrls.length,page_errors:errors,server_errors:serverErrors},null,2));
  console.log('READ-ONLY EKS INVENTORY / BOTH THEMES / INGRESS QUERY BOUNDS PASS');
}finally{await browser.close();}
