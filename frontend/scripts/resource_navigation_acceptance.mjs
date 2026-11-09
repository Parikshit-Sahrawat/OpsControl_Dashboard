// Real authenticated FastAPI/PostgreSQL/Vite navigation; no mocked backend.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {chromium} = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const fixture = JSON.parse(await readFile(process.env.V16_PRIVATE_DIR+'/browser-fixture.json','utf8'));
const browser = await chromium.launch({headless:true, executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const out=process.env.V16_EVIDENCE_DIR, base=process.env.V16_API_URL, ui=process.env.V16_UI_URL;
const checks=[], trace=[], screenshots=[];
let active, phase='login';
const domains=[['Compute Instances','compute-instances','VM','Navigation VM'],['Data Pipelines','data-pipelines','ETL','Navigation ETL'],['APIs','apis','API','Navigation API']];
async function login(name,password,section='compute-instances') {
  const page=await browser.newPage({viewport:{width:1440,height:900}});active=page;
  await page.addInitScript(id=>{localStorage.setItem('opscontrol.organizationIds',JSON.stringify([id]));localStorage.setItem('opscontrol.theme','light');},fixture.organization_id);
  page.on('response',response=>{if(response.url().includes('/api/'))trace.push({phase,path:new URL(response.url()).pathname,status:response.status()});});
  await page.goto(ui+'/#/resources/'+section);
  await page.getByLabel('Username',{exact:true}).fill(name);
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  await page.getByRole('button',{name:'Sign out',exact:true}).waitFor();
  return page;
}
async function request(page,path,method='GET',data,expected=200,customer=fixture.organization_id) {
  const token=await page.evaluate(()=>sessionStorage.getItem('opscontrol.sessionToken'));
  const response=await page.request.fetch(base+'/api/v1/'+path,{method,data,headers:{Authorization:'Bearer '+token,'X-OpsControl-Customers':customer}});
  assert.equal(response.status(),expected,method+' '+path);
  return expected===204?null:response.json();
}
async function selected(page,label,section,domain,name) {
  await page.waitForURL(url=>url.hash==='#/resources/'+section);
  const nav=page.getByRole('navigation',{name:'Primary navigation'});
  await nav.getByRole('button',{name:label,exact:true}).waitFor();
  assert.equal(await nav.getByRole('button',{name:label,exact:true}).getAttribute('aria-current'),'page');
  await page.getByRole('heading',{name:domain==='API'?'API Endpoints':label,exact:true}).waitFor();
  await page.getByRole('row').filter({hasText:name}).waitFor();
  await page.waitForURL(url=>url.searchParams.get('rm.domain')===domain);
  assert.equal(await page.locator('.workspace-breadcrumb b').textContent(),label);
  const rows=await request(page,'unified/resources?domain='+domain+'&organization_id='+fixture.organization_id);
  assert.ok(rows.items.some(row=>row.name===name));
  assert.ok(rows.items.every(row=>row.domain===domain && row.organization_id===fixture.organization_id));
}
try {
  const admin=await login('v16-api-admin',fixture.password);
  await admin.getByLabel('Search resources',{exact:true}).waitFor();
  phase='seed owned inventory';
  const vm=await request(admin,'unified/resources/vm','POST',{name:'Navigation VM',organization_id:fixture.organization_id,environment:'PROD',hostname:'navigation.invalid',address:'203.0.113.202',os_type:'Linux'},201);
  const etl=await request(admin,'unified/resources/etl','POST',{name:'Navigation ETL',organization_id:fixture.organization_id,environment:'PROD',platform:'PENTAHO',jobchain:'navigation-read-only'},201);
  const api=await request(admin,'unified/resources/api','POST',{name:'Navigation API',organization_id:fixture.organization_id,environment:'PROD',dns:'navigation-api.invalid'},201);
  const owned=[vm,etl,api];
  // No connectivity probes, provider workloads or activation are requested.
  for (const [role,page] of [['admin',admin],['operator',await login('s01-noc-operator',fixture.viewer_password)]]) {
    active=page;phase=role+' domains';
    await page.getByLabel('Resource customer filter',{exact:true}).selectOption(fixture.organization_id);
    await page.getByLabel('Resource environment filter',{exact:true}).selectOption('PROD');
    for (const [label,section,domain,name] of domains) {
      const nav=page.getByRole('navigation',{name:'Primary navigation'});
      const category=nav.getByRole('button',{name:'Resource Management navigation',exact:true});
      if(await category.getAttribute('aria-expanded')!=='true')await category.click();
      await nav.getByRole('button',{name:label,exact:true}).click();
      await selected(page,label,section,domain,name);
      assert.equal(new URL(page.url()).searchParams.get('rm.customer'),fixture.organization_id);
      assert.equal(await page.getByLabel('Resource environment filter',{exact:true}).inputValue(),'PROD');
      assert.equal(await nav.getByRole('button',{name:'Data Sources / Resources',exact:true}).count(),0);
      assert.equal(await nav.getByRole('button',{name:'Resource Management workspace navigation',exact:true}).count(),0);
      for (const [width,height] of [[1920,1080],[1440,900],[1366,768]]) {
        await page.setViewportSize({width,height});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        const shot='navigation-'+role+'-'+domain+'-'+width+'x'+height+'.png';
        await page.screenshot({path:out+'/'+shot,fullPage:false});screenshots.push(shot);
      }
      await page.reload();await selected(page,label,section,domain,name);
      if(role==='operator') {
        assert.equal(await page.getByRole('button',{name:/^Create (Compute Instance|Legacy Data Pipeline|API Endpoint)$/}).count(),0);
        assert.equal(await page.getByRole('row').filter({hasText:name}).getByRole('button',{name:'Edit',exact:true}).count(),0);
      }
      checks.push(role+' '+domain+' inventory: actual HTTP persistence, tenant/env filters, reload, active item/breadcrumb and three desktop sizes');
    }
    phase=role+' history';
    // Explicit sequence separates back/forward assertions from reload history.
    const nav=page.getByRole('navigation',{name:'Primary navigation'});
    for(const [label,section,domain,name] of domains){await nav.getByRole('button',{name:label,exact:true}).click();await selected(page,label,section,domain,name);}
    await page.goBack();await selected(page,...domains[1]);
    await page.goBack();await selected(page,...domains[0]);
    await page.goForward();await selected(page,...domains[1]);
    await page.goForward();await selected(page,...domains[2]);
    const category=nav.getByRole('button',{name:'Resource Management navigation',exact:true});
    await category.focus();await page.keyboard.press('ArrowLeft');assert.equal(await category.getAttribute('aria-expanded'),'false');
    await page.keyboard.press('ArrowRight');assert.equal(await category.getAttribute('aria-expanded'),'true');
    const compute=nav.getByRole('button',{name:'Compute Instances',exact:true});await compute.focus();await page.keyboard.press('Enter');await selected(page,...domains[0]);
    await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click();
    await nav.getByRole('button',{name:'Resource Management navigation',exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'Collapse sidebar',exact:true}).count(),1);
    await nav.getByRole('button',{name:'APIs',exact:true}).click();await selected(page,...domains[2]);
    await page.reload();await selected(page,...domains[2]);
    const ops=nav.getByRole('button',{name:'Operations navigation',exact:true});if(await ops.getAttribute('aria-expanded')!=='true')await ops.click();
    await nav.getByRole('button',{name:'Compute Health',exact:true}).click();await page.waitForURL(url=>url.hash==='#/operations/compute-health');
    assert.equal(await page.getByRole('button',{name:'Create Compute Instance',exact:true}).count(),0);
    await page.goBack();await selected(page,...domains[2]);
    checks.push(role+' back/forward, keyboard navigation, expansion persistence, collapse/expand and separate Operations route');
    if(role==='operator'){
      for(const row of owned)await request(page,'unified/resources/'+row.id,'PUT',{expected_revision:row.revision,name:'Forbidden navigation edit'},403);
      const foreign=await page.request.get(base+'/api/v1/unified/resources?domain=VM&organization_id='+fixture.other_organization_id,{headers:{Authorization:'Bearer '+await page.evaluate(()=>sessionStorage.getItem('opscontrol.sessionToken')),'X-OpsControl-Customers':fixture.organization_id}});
      assert.ok([200,403,404].includes(foreign.status()));if(foreign.status()===200)assert.equal((await foreign.json()).items.length,0);
      checks.push('Operator mutations denied for VM/ETL/API and foreign-customer inventory denied/empty');
    }
  }
  phase='ungranted account';active=admin;
  const dep=await request(admin,'access/departments','POST',{name:'Navigation no grants',code:'NAV-NONE'},201);
  await request(admin,'auth/users','POST',{username:'nav-no-resource-grant',password:fixture.viewer_password,platform_admin:false,department_id:dep.id},201);
  const denied=await login('nav-no-resource-grant',fixture.viewer_password);active=denied;
  for(const [label,section,domain] of domains){
    await denied.goto(ui+'/#/resources/'+section);await denied.getByRole('button',{name:'Sign out',exact:true}).waitFor();
    assert.equal(await denied.getByRole('navigation',{name:'Primary navigation'}).getByRole('button',{name:label,exact:true}).count(),0);
    assert.equal(await denied.getByRole('heading',{name:domain==='API'?'API Endpoints':label,exact:true}).count(),0);
    await request(denied,'unified/resources?domain='+domain,'GET',undefined,403);
  }
  checks.push('No resources.view: all three management links/direct routes withheld and real domain APIs403');
  await writeFile(out+'/resource-navigation.json',JSON.stringify({status:'PASS',checks,screenshots,trace,fixture:'Owned PostgreSQL synthetic records;no provider activation',permissions:'Existing resources.view governs all resource inventories;no new domain permission catalogue'},null,2));
  console.log('RESOURCE NAVIGATION BROWSER PASS '+checks.length+' groups');
} catch(error){
  await active?.screenshot({path:out+'/resource-navigation-failure.png',fullPage:true});
  await writeFile(out+'/resource-navigation-failure.json',JSON.stringify({phase,error:error.name,message:String(error.message).replace(/Bearer\s+\S+/g,'Bearer [REDACTED]'),trace},null,2));
  throw error;
} finally {await browser.close();}
