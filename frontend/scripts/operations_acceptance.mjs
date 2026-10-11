// Real Chromium, password login and backend responses; no mocked health data.
import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const state=JSON.parse(await readFile(process.env.ETL_SESSION_FILE,'utf8'));
const phase=process.argv[2],output=process.env.OPERATIONAL_EVIDENCE_DIR;
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const errors=[],serverErrors=[],checks=[];
async function login(who){
  const page=await browser.newPage({viewport:{width:1600,height:1100}});page.on('pageerror',e=>errors.push(e.message));
  page.on('response',response=>{if(response.url().includes('/api/')&&response.status()>=500)serverErrors.push(response.status());});
  await page.goto('http://127.0.0.1:15174');
  await page.getByRole('textbox',{name:'Username'}).fill(who==='admin'?'demo-admin':state[who+'_username']);
  await page.getByLabel('Password').fill(who==='admin'?await readFile(process.env.ETL_PRIVATE_DIR+'/admin-password','utf8'):state[who+'_password']);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('heading',{name:'Overview',exact:true}).waitFor();return page;
}
const tab=async(page,name)=>{
  // Modal investigations must close before navigating the workspace behind them.
  const close=page.getByRole('button',{name:'Close evidence',exact:true});
  if(await close.isVisible())await close.click();
  const jobClose=page.getByRole('button',{name:'Close drawer',exact:true});
  if(await jobClose.isVisible())await jobClose.click();
  await page.getByRole('button',{name,exact:true}).first().click();
};
const shot=async(page,name)=>page.screenshot({path:`${output}/${name}.png`,fullPage:true});
async function chooseOrganization(page,name){
  await page.locator('.org-context-button').click();
  await page.getByRole('checkbox',{name:new RegExp('^'+name)}).check();
  const menu=page.locator('.org-menu');const boxes=menu.getByRole('checkbox');
  for(let i=1;i<await boxes.count();i++){
    const box=boxes.nth(i);const label=await box.locator('..').innerText();
    if(!label.startsWith(name)&&await box.isChecked())await box.uncheck();
  }
  await page.locator('.org-context-button').click();
}
try{
  const page=await login('reader');
  await page.getByRole('button',{name:'Open APIs & Services'}).click();
  await page.getByRole('heading',{name:'APIs',exact:true}).waitFor();
  const service=page.getByTestId('service-row').filter({hasText:'Fictional NOC HTTPS Portal'});
  await service.getByText(phase==='failed'?'CRITICAL':'HEALTHY',{exact:true}).waitFor();
  await page.getByTestId('service-row').filter({hasText:'Unobserved NOC Service'}).getByText('UNKNOWN',{exact:true}).waitFor();
  await page.getByTestId('service-row').filter({hasText:'Disabled NOC Service'}).getByText('DISABLED',{exact:true}).waitFor();
  await page.getByLabel('Search services').fill('Fictional NOC');assert.equal(await page.getByTestId('service-row').count(),1);
  await page.getByLabel('Search services').fill('');
  await page.getByRole('button',{name:/^UNKNOWN\s+1$/}).click();assert.equal(await page.getByTestId('service-row').count(),1);
  await page.getByLabel('Service health').selectOption('ALL');
  await service.getByRole('button',{name:'Fictional NOC HTTPS Portal'}).click();
  await page.getByRole('dialog').getByRole('heading',{name:'Operational history'}).waitFor();
  assert.equal(await page.getByRole('dialog').getByRole('row').count(),phase==='configured'?2:phase==='failed'?3:4);
  await shot(page,`apis-${phase}`);await page.getByRole('button',{name:'Close evidence'}).click();
  checks.push('API evidence, status, search, clickable health KPI and history');
  if(phase!=='configured'){
    await tab(page,'Incidents');await page.getByLabel('Search incidents').fill('noc-http-unavailable');
    await page.getByRole('button',{name:/noc-http-unavailable/}).click();
    await page.getByRole('dialog').getByText('SOURCE_OPENED',{exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Mark ACKNOWLEDGED'}).count(),0);
    assert.equal(await page.getByLabel('Investigation note',{exact:true}).count(),0);
    await shot(page,`incidents-viewer-${phase}`);
    const operator=await login('operator');await tab(operator,'Incidents');
    await operator.getByLabel('Search incidents').fill('noc-http-unavailable');
    await operator.getByRole('button',{name:/noc-http-unavailable/}).click();
    const drawer=operator.getByRole('dialog');
    if(phase==='failed'){
      await drawer.getByRole('button',{name:'Mark ACKNOWLEDGED',exact:true}).click();
      await drawer.getByRole('button',{name:'Mark INVESTIGATING',exact:true}).click();
      assert.equal(await drawer.getByRole('button',{name:'Mark RESOLVED',exact:true}).count(),0);
      await drawer.getByLabel('Investigation note',{exact:true}).fill('Browser verified HTTP 503 evidence and began the local incident investigation.');
      await drawer.getByRole('button',{name:'Save incident note'}).click();
      await drawer.getByText('Browser verified HTTP 503 evidence and began the local incident investigation.',{exact:true}).waitFor();
    }else{
      await drawer.getByText('SOURCE_RECOVERED',{exact:true}).waitFor();
      await drawer.getByRole('button',{name:'Mark RESOLVED',exact:true}).click();
      await drawer.getByText('OPERATOR_TRANSITION · RESOLVED',{exact:true}).waitFor();
    }
    await shot(operator,`incident-operator-${phase}`);
    checks.push('Viewer read-only; actual operator acknowledgement, investigation, note and gated resolution');
    if(phase==='recovered'){
      await operator.getByRole('button',{name:'Close evidence'}).click();await operator.getByLabel('Search incidents').fill('');
      await operator.getByLabel('Incident source').selectOption('ETL');
      await operator.getByRole('button',{name:/Fictional Daily Warehouse · JOB_FAILED/}).click();
      await operator.getByRole('button',{name:'Investigate ETL execution'}).click();
      await operator.getByRole('dialog').getByText('controlled-failed',{exact:true}).waitFor();
      await operator.getByRole('dialog').getByText('RESOURCE_ALERT',{exact:true}).waitFor();
      await shot(operator,'incident-etl-investigation');
      checks.push('Incident drill-down opens historical ETL failure and host correlation');
    }
  }
  if(phase==='recovered'){
    await tab(page,'Reports');await page.getByRole('heading',{name:'HTTP sampled success'}).waitFor();
    await page.getByText('66.67%',{exact:true}).waitFor();await page.getByText('100%',{exact:true}).waitFor();
    await page.getByLabel('Report window').selectOption('1');await page.getByText('66.67%',{exact:true}).waitFor();
    await page.getByLabel('History type').selectOption('ETL');await page.getByRole('row').filter({hasText:'Fictional Daily Warehouse'}).first().waitFor();
    await shot(page,'reports');
    const downloadWait=page.waitForEvent('download');await page.getByRole('button',{name:'Export report JSON'}).click();
    const download=await downloadWait;const exported=JSON.parse(await readFile(await download.path(),'utf8'));
    assert.equal(exported.services[0].sample_success_percent,66.67);assert.equal(exported.days,1);assert.equal(exported.etl[0].sla_excluded,4);
    await page.getByLabel('History type').selectOption('COLLECTOR');
    await page.getByRole('button',{name:'Controlled HTTPS Carte',exact:true}).first().click();
    await page.getByRole('dialog').getByText('FAILED',{exact:true}).first().waitFor();await shot(page,'reports-collector-history');
    await page.getByRole('button',{name:'Close evidence'}).click();await page.getByLabel('History type').selectOption('ETL');
    await page.getByRole('button',{name:'Fictional Daily Warehouse',exact:true}).first().click();
    await page.getByRole('dialog').getByRole('button',{name:'controlled-failed',exact:true}).click();
    await page.getByRole('dialog').getByText('controlled-failed',{exact:true}).waitFor();await shot(page,'reports-etl-history');
    checks.push('Report window, exact denominators, JSON export, history filter and execution drill-down');
    await tab(page,'Overview');await page.getByRole('button',{name:'Open ETL Jobs',exact:true}).click();
    await page.getByRole('heading',{name:'ETL Jobs',exact:true}).waitFor();
    await page.getByRole('row').filter({hasText:'Fictional Daily Warehouse'}).getByText('SUCCESS',{exact:true}).waitFor();await shot(page,'etl-jobs');
    await tab(page,'Overview');await page.getByRole('button',{name:'Open VM Health',exact:true}).click();
    const host=page.getByTestId('infrastructure-row').filter({hasText:'ETL live Linux worker'});
    await host.getByText('HEALTHY',{exact:true}).waitFor();await host.getByRole('button',{name:'ETL live Linux worker'}).click();
    await page.getByTestId('infrastructure-detail').getByRole('heading',{name:'Operational history'}).waitFor();await shot(page,'vm-health');
    await tab(page,'Overview');await page.getByRole('button',{name:'Open Active Incidents',exact:true}).click();
    await page.getByRole('heading',{name:'Incidents',exact:true}).waitFor();
    await page.getByRole('button',{name:/^RESOLVED\s+1$/}).click();await page.getByTestId('incident-row').filter({hasText:'noc-http-unavailable'}).waitFor();
    await tab(page,'Overview');await page.getByRole('button',{name:'Open APIs & Services',exact:true}).waitFor();await shot(page,'overview');
    checks.push('All four Overview KPI targets, VM resource/collector/alert history and ETL rows');
    const admin=await login('admin');await chooseOrganization(admin,'Controlled ETL Lab');
    await tab(admin,'Resource Management');await admin.locator('.resource-sidebar').getByRole('button',{name:/^Data Sources/}).click();
    await admin.getByText('Fictional NOC HTTPS Portal',{exact:true}).first().waitFor();await shot(admin,'resource-management');
    await tab(admin,'Monitoring Setup');await admin.getByRole('heading',{name:'Monitoring Setup',exact:true}).waitFor();
    await admin.getByRole('option',{name:/Fictional NOC HTTPS Portal/}).waitFor({state:'attached'});await shot(admin,'monitoring-setup');
    await tab(admin,'Access Management');await admin.getByRole('cell',{name:'etl-operator',exact:true}).first().waitFor();await shot(admin,'access-management');
    checks.push('Resource Management, Monitoring Setup and platform Access Management backend screens');
    await tab(admin,'APIs');await admin.getByTestId('service-row').filter({hasText:'Fictional NOC HTTPS Portal'}).waitFor();
    // Delay real responses to expose races when changing authorized UI scope.
    await admin.route('**/api/v1/operations/services?**',async route=>{await new Promise(r=>setTimeout(r,750));try{await route.continue();}catch{}});
    await admin.getByRole('button',{name:'Refresh services'}).click();
    await chooseOrganization(admin,'Other ETL Tenant');
    await admin.getByTestId('service-row').filter({hasText:'Other Tenant Private Service'}).waitFor();
    await admin.waitForTimeout(1000);assert.equal(await admin.getByTestId('service-row').filter({hasText:'Fictional NOC HTTPS Portal'}).count(),0);
    await shot(admin,'organization-switch');await tab(admin,'Reports');
    await admin.getByText('No HTTP observations in this organization and report window.',{exact:true}).waitFor();
    await admin.getByText('No ETL executions in this organization and report window.',{exact:true}).waitFor();
    const other=await login('other');await tab(other,'Incidents');await other.getByText('No incidents match this organization and filters.',{exact:true}).waitFor();await shot(other,'tenant-isolation');
    checks.push('Authorized organization change ignores delayed old response; other tenant gets empty incident and report evidence');
    // Mobile layout remains operable with a genuine backend response.
    await page.setViewportSize({width:390,height:844});await tab(page,'APIs');await service.waitFor();await shot(page,'mobile-apis');
  }
  assert.deepEqual(errors,[]);assert.deepEqual(serverErrors,[]);
  await writeFile(`${output}/browser-${phase}.json`,JSON.stringify({phase,checks,page_errors:errors,server_errors:serverErrors,chromium_version:browser.version(),status:'PASS'},null,2)+'\n');
  console.log(`PLAYWRIGHT NOC ${phase} PASS: ${checks.join('; ')}`);
}catch(error){
  for(const context of browser.contexts())for(const page of context.pages())await page.screenshot({path:'/tmp/noc-browser-failure-'+browser.contexts().indexOf(context)+'.png',fullPage:true});
  throw error;
}finally{await browser.close();}
