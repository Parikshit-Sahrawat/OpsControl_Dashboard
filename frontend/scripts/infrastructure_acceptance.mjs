// Real browser login, backend reads, filters and screenshots.
import assert from 'node:assert/strict';
import {readFile,mkdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE?pathToFileURL(process.env.PLAYWRIGHT_MODULE).href:'playwright');
const state=JSON.parse(await readFile(process.env.INFRA_SESSION_FILE,'utf8'));
const phase=process.argv[2],output=process.env.INFRA_EVIDENCE_DIR;
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE?{executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE}:{})});
const errors=[];
async function login(who){
  const page=await browser.newPage({viewport:{width:1600,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:15173');
  await page.getByRole('textbox',{name:'Username'}).fill(state[who+'_username']);
  await page.getByLabel('Password').fill(state[who+'_password']);
  await page.getByRole('button',{name:'Sign in'}).click();
  await page.getByRole('button',{name:'VM Health',exact:true}).click();return page;
}
try{
  const page=await login('reader');
  const health=phase==='configured'?'UNKNOWN':phase==='failed'?'CRITICAL':'HEALTHY';
  for(const resource of state.resources){
    const row=page.getByTestId('infrastructure-row').filter({hasText:resource.name});
    await row.getByRole('button',{name:resource.name,exact:true}).waitFor();
    await row.getByRole('cell',{name:health,exact:true}).waitFor();
  }
  await page.getByRole('button',{name:`Filter ${health}`,exact:true}).click();
  assert.equal(await page.getByTestId('infrastructure-row').count(),6);
  await page.getByLabel('Provider',{exact:true}).selectOption('LINUX_HOST');
  await page.getByLabel('Search infrastructure').fill('Linux');
  assert.equal(await page.getByTestId('infrastructure-row').count(),1);
  await page.getByRole('button',{name:'Linux live worker',exact:true}).click();
  const detail=page.getByTestId('infrastructure-detail');
  if(phase!=='configured'){
    await detail.getByText(/"cpu_percent":/).waitFor();
    await detail.getByText(/"process_running":/).waitFor();
    if(phase==='failed')await detail.getByText(/OPEN · CRITICAL/).waitFor();
    if(phase==='recovered')await detail.getByText(/RESOLVED · CRITICAL/).waitFor();
  }
  await page.getByLabel('Provider',{exact:true}).selectOption('ALL');await page.getByLabel('Search infrastructure').fill('');
  await page.screenshot({path:`${output}/${phase}.png`,fullPage:true});
  if(phase==='recovered'){
    const other=await login('other');
    await other.getByText('No infrastructure resources match this organization and filters.',{exact:true}).waitFor();
    assert.equal(await other.getByTestId('infrastructure-row').count(),0);
    await other.screenshot({path:`${output}/other-tenant.png`,fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log(`PLAYWRIGHT infrastructure ${phase} PASS`);
}finally{await browser.close();}
