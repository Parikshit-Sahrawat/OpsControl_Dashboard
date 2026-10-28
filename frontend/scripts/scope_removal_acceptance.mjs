// Actual Chromium + authenticated owned API; no route mocking or source searches.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {scopeHeaders} from './explicit_scope.mjs';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
const page=await browser.newPage({viewport:{width:1600,height:1100}});
const out=process.env.RELEASE_EVIDENCE_DIR,base=process.env.TEST_API_BASE,ui=process.env.RELEASE_UI_BASE;
const checks=[],errors=[];
let apiResource;
page.on('pageerror',e=>errors.push(e.name));
const excluded=/\b(kubernetes|k8s|eks|aks|gke|openshift)\b/i;
async function absentControls(){
  const labels=await page.locator('button,a,select option,[role=tab]').allTextContents();
  assert.equal(labels.filter(x=>excluded.test(x)).length,0);
  assert.equal(await page.getByText('Imported discovery inventory',{exact:true}).count(),0);
}
try{
 await mkdir(out,{recursive:true});
 await page.goto(ui);
 await page.getByLabel('Username').fill('test-north');
 await page.getByLabel('Password').fill('testing-only-StrongPassword-123!');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('heading',{name:'Dashboard',exact:true}).waitFor();
 await absentControls();checks.push('Authenticated navigation has no excluded controls');
 const token=await page.evaluate(()=>sessionStorage.getItem('opscontrol.sessionToken'));
 const headers=await scopeHeaders(page.request,base,token);
 const org=(await (await page.request.get(base+'/api/v1/auth/customer-scope',{headers})).json())[0].id;
 for(const [name,os,vm] of [['scope-linux','Linux','VM'],['scope-windows','Windows','VM'],['scope-ec2','Linux','EC2']]){
   const response=await page.request.post(base+'/api/v1/unified/resources/vm',{headers,data:{organization_id:org,name,environment:'DEV',hostname:name+'.example.test',address:name+'.example.test',os_type:os,vm_type:vm}});
   assert.equal(response.status(),201,await response.text());
 }
 for(const [kind,data] of [['api',{name:'scope-api',dns:'scope-api.example.test'}],['etl',{name:'scope-pentaho',platform:'PENTAHO',jobchain:'scope-readonly'}]]){
   const response=await page.request.post(base+'/api/v1/unified/resources/'+kind,{headers,data:{organization_id:org,environment:'DEV',...data}});
   assert.equal(response.status(),201,await response.text());
   if(kind==='api')apiResource=await response.json();
 }
 await page.getByRole('button',{name:'Data Sources / Resources',exact:true}).click();
 for(const name of ['scope-linux','scope-windows','scope-ec2']){
   await page.getByLabel('Search resources',{exact:true}).fill(name);
   const row=page.getByRole('row').filter({hasText:name});await row.waitFor();
   await row.getByRole('button',{name:'Edit',exact:true}).click();
   const modal=page.getByRole('region',{name:'Edit Compute Instance',exact:true});
   await modal.getByLabel('Resource name',{exact:true}).fill(name+' reviewed');
   await modal.getByRole('button',{name:'Save resource',exact:true}).click();await modal.waitFor({state:'hidden'});
   checks.push(name+' real inventory edit/save');
 }
 await page.getByLabel('Search resources',{exact:true}).fill('scope-legacy-do-not-operate');
 assert.equal(await page.getByRole('row').filter({hasText:'scope-legacy-do-not-operate'}).count(),0);
 checks.push('Legacy cluster source is absent from actionable Compute inventory');
 await page.getByLabel('Search resources',{exact:true}).fill('');
 await page.screenshot({path:out+'/scope-compute.png',fullPage:true});
 await page.getByRole('tab',{name:'API Endpoints',exact:true}).click();
 await page.getByLabel('Search resources',{exact:true}).fill('scope-api');
 await page.getByRole('row').filter({hasText:'scope-api'}).waitFor();
 await absentControls();checks.push('Persisted API resource visible; excluded selectors absent');
 const templates=await (await page.request.get(base+'/api/v1/monitoring/templates',{headers})).json();
 const template=templates.find(t=>t.name==='scope-supported-template');assert.ok(template);
 const attached=await page.request.post(base+'/api/v1/monitoring/data-sources/'+apiResource.data_source_id+'/templates',{headers,data:{template_id:template.id}});
 assert.equal(attached.status(),201,await attached.text());
 await page.getByRole('button',{name:'scope-api',exact:true}).click();
 await page.getByRole('button',{name:'Open legacy monitoring configuration',exact:true}).click();
 const include=page.getByLabel('Include attached Monitoring Template bundles',{exact:true});
 await include.waitFor();assert.equal(await include.isChecked(),false);
 await include.check();assert.equal(await include.isChecked(),true);
 await include.uncheck();assert.equal(await include.isChecked(),false);await include.check();
 const persisted=await (await page.request.get(base+'/api/v1/monitoring/data-sources/'+apiResource.data_source_id+'/templates',{headers})).json();
 assert.ok(persisted.some(t=>t.template_id===template.id));
 checks.push('Template attachment persisted; real Monitoring Setup bundle selection works');
 await page.screenshot({path:out+'/scope-api.png',fullPage:true});
 await page.getByRole('tab',{name:'Data Pipelines',exact:true}).click();
 await absentControls();
 await page.getByRole('button',{name:'Create Data Pipeline',exact:true}).click();
 const wizard=page.getByRole('region',{name:'Data Pipelines eight-step wizard',exact:true});
 await wizard.getByLabel('Integration name',{exact:true}).fill('scope-pentaho-browser');
 await wizard.getByLabel('Organization',{exact:true}).selectOption(org);
 await wizard.getByLabel('Environment',{exact:true}).selectOption('DEV');
 await wizard.getByRole('button',{name:'Save / resume draft',exact:true}).click();
 await page.getByText('Saved. Configuration saving does not certify deployment or data reception.',{exact:true}).waitFor();
 checks.push('Pentaho browser wizard saves persisted draft; no provider execution/certification');
 await page.screenshot({path:out+'/scope-pipelines.png',fullPage:true});
 for(const path of ['/#/resources/kubernetes-clusters','/#/kubernetes','/kubernetes','/clusters','/eks','/aks','/gke','/openshift']){
   await page.goto(ui+path);await page.waitForLoadState('networkidle');await absentControls();
   checks.push('No operational cluster controls after direct navigation '+path);
 }
 assert.deepEqual(errors,[]);
 await writeFile(out+'/scope-browser.json',JSON.stringify({status:'PASS',checks,assertion_groups:checks.length,page_errors:errors,
   limitations:['Synthetic configured resources; no genuine provider execution','Pentaho browser draft is configuration acceptance, not genuine runtime certification']},null,2));
 console.log('SCOPE REMOVAL BROWSER PASS',checks.length);
}catch(e){await page.screenshot({path:out+'/scope-browser-failed.png',fullPage:true});throw e;}
finally{await browser.close();}
