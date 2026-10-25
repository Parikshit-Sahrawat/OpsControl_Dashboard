// Reuse baseline real-browser checks, adding an actual reload before diagnostics.
import { readFile, writeFile } from 'node:fs/promises';
const source = await readFile('/repo/frontend/scripts/http_golden_path.mjs', 'utf8');
const anchor = "  const lockedSource = page.locator('.monitoring-setup select').first();";
if (!source.includes(anchor)) throw Error('Baseline browser adapter anchor changed');
let adapted = source.replace(anchor, `
  await page.reload();
  await page.getByRole('button',{name:'Data Sources / Resources',exact:true}).click();
  await page.getByRole('tab',{name:'API Endpoints',exact:true}).click();
  await page.getByRole('button',{name:'Fictional HTTPS Portal',exact:true}).click();
  await page.getByRole('button',{name:'Open legacy monitoring configuration',exact:true}).click();
  await page.waitForFunction(expected => [...document.querySelectorAll('select')].some(select => select.disabled && select.value === expected), state.source_id);
${anchor}`);
adapted = adapted.replace("  assert.deepEqual(errors,[]);", `
  if (phase !== 'configured') {
    const [response]=await Promise.all([
      page.waitForResponse(r=>r.url().includes('/api/v1/unified/overview?')&&r.request().method()==='GET'),
      page.getByRole('button',{name:'Go to Dashboard',exact:true}).click()
    ]);
    assert.equal(response.status(),200);
    const summary=await response.json();
    const active=summary.alerts.filter(a=>a.domain==='API'&&a.status==='OPEN'&&a.resource_name==='Fictional HTTPS Portal');
    assert.equal(active.length,phase==='failed'?1:0);
    const section=page.locator('section').filter({has:page.getByRole('heading',{name:'API Endpoint Alerts',exact:true})});
    if (phase==='failed') await section.getByRole('button',{name:'Fictional HTTPS Portal',exact:true}).waitFor();
    await page.screenshot({path:output+'/dashboard-'+phase+'.png',fullPage:true});
  }
  assert.deepEqual(errors,[]);`);
adapted=adapted.replace("  page.on('pageerror'","  page.setDefaultTimeout(15000);\n  console.log('Chromium:',browser.version());\n  page.on('pageerror'");
// Do not retain failure screenshots of login forms containing passwords.
const safe = adapted.replace("if (page) await page.screenshot", "if (page) await page.locator('input[type=password]').fill('').catch(()=>{});\n  if (page) await page.screenshot");
await writeFile('/tmp/dev05-browser.mjs', safe);
await import('file:///tmp/dev05-browser.mjs');
