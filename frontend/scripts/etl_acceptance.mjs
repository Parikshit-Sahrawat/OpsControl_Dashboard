// Real password login and data-backed ETL drawer checks; no mocked API responses.
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE?pathToFileURL(process.env.PLAYWRIGHT_MODULE).href:'playwright');
const state=JSON.parse(await readFile(process.env.ETL_SESSION_FILE,'utf8'));
const phase=process.argv[2],output=process.env.ETL_EVIDENCE_DIR;
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
const errors=[];
async function login(who){
  const page=await browser.newPage({viewport:{width:1600,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:15174');
  await page.getByRole('textbox',{name:'Username'}).fill(state[who+'_username']);
  await page.getByLabel('Password').fill(state[who+'_password']);
  await page.getByRole('button',{name:'Sign in'}).click();
  await page.getByRole('button',{name:'ETL Jobs',exact:true}).click();return page;
}
try{
  const page=await login('reader');
  if(phase==='configured'){
    await page.getByRole('heading',{name:'No executions found'}).waitFor();
  }else{
    const expected={'no-run':'NO RUN',running:'RUNNING','long-running':'LONG RUNNING','sla-breach':'LONG RUNNING',failed:'FAILED','poll-failed':'FAILED',recovered:'SUCCESS'}[phase];
    const row=page.getByRole('row').filter({hasText:'Fictional Daily Warehouse'});
    await row.getByText(expected,{exact:true}).waitFor();
    await row.getByText(phase==='poll-failed'?'ERROR':'CURRENT',{exact:true}).waitFor();
    if(phase==='sla-breach')await row.getByText('SLA breach',{exact:true}).waitFor();
    await row.click();
    const drawer=page.getByRole('dialog');
    await drawer.getByText(phase==='no-run'?'NO_RUN_OPEN':`controlled-${phase==='poll-failed'?'failed':phase}`,{exact:phase!=='no-run'}).first().waitFor();
    if(phase!=='no-run'){
      await drawer.getByText('Load warehouse',{exact:true}).first().waitFor();
      await drawer.getByText(/password=\[REDACTED\]/).waitFor();
      assert.equal(await drawer.getByText('fixture-sensitive-marker',{exact:false}).count(),0);
    }
    if(phase==='failed'){
      await drawer.getByText('RESOURCE_ALERT',{exact:true}).waitFor();
      await drawer.getByText('Warehouse connection refused',{exact:false}).first().waitFor();
      assert.equal(await drawer.getByPlaceholder('Add chronological operator note...').count(),0);
      const operator=await login('operator');
      await operator.getByRole('row').filter({hasText:'Fictional Daily Warehouse'}).click();
      await operator.getByRole('button',{name:'Move to INVESTIGATING',exact:true}).click();
      await operator.getByPlaceholder('Add chronological operator note...').fill('Browser investigation verified the source failure and live host correlation.');
      await operator.getByRole('button',{name:'Add Note',exact:true}).click();
      await operator.getByText('Browser investigation verified the source failure and live host correlation.',{exact:true}).waitFor();
      await operator.screenshot({path:`${output}/investigation.png`,fullPage:true});
    }
    if(phase==='recovered'){
      await drawer.getByText(/JOB_FAILED_RESOLVED/).first().waitFor();
      await drawer.getByText(/controlled-failed/).first().waitFor();
    }
  }
  await page.screenshot({path:`${output}/${phase}.png`,fullPage:true});
  if(phase==='recovered'){
    await page.getByRole('dialog').getByRole('button',{name:/controlled-failed/}).click();
    await page.getByRole('dialog').getByText('controlled-failed',{exact:true}).waitFor();
    await page.getByRole('dialog').getByText('INVESTIGATING',{exact:true}).waitFor();
    await page.getByRole('dialog').getByText('RESOURCE_ALERT',{exact:true}).waitFor();
    await page.screenshot({path:`${output}/historical-failure.png`,fullPage:true});
    const other=await login('other');
    await other.getByRole('heading',{name:'No executions found'}).waitFor();
    assert.equal(await other.getByText('Fictional Daily Warehouse',{exact:true}).count(),0);
    await other.screenshot({path:`${output}/other-tenant.png`,fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log(`PLAYWRIGHT ETL ${phase} PASS`);
}catch(error){
  const page=browser.contexts().flatMap(context=>context.pages())[0];
  if(page)await page.screenshot({path:'/tmp/etl-browser-failure.png',fullPage:true});
  throw error;
}finally{await browser.close();}
