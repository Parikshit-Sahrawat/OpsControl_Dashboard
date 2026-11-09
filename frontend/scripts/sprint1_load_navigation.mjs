import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const f=JSON.parse(await readFile(process.env.V16_PRIVATE_DIR+'/browser-fixture.json','utf8'));
const browser=await chromium.launch({headless:true});
try {
 const page=await browser.newPage({viewport:{width:1280,height:800}});let requests=0,errors=0;
 page.on('response',r=>{if(r.url().includes('/api/')){requests++;if(r.status()>=500) errors++;}});
 const start=performance.now();await page.goto(process.env.V16_UI_URL);
 await page.getByLabel('Username').fill('v16-api-admin');await page.getByLabel('Password').fill(f.password);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('heading',{name:'Dashboard',exact:true}).waitFor();const loginMs=performance.now()-start;
 const nav=performance.now();await page.getByRole('button',{name:'Compute Instances',exact:true}).click();
 await page.getByRole('button',{name:'Create Compute Instance',exact:true}).waitFor();const navigationMs=performance.now()-nav;
 const lag=await page.evaluate(async()=>{const t=performance.now();await new Promise(r=>setTimeout(r,50));return performance.now()-t-50;});
 assert.equal(errors,0);
 await writeFile(process.env.V16_EVIDENCE_DIR+'/load-navigation.json',JSON.stringify({status:'PASS',login_render_ms:loginMs,resource_navigation_ms:navigationMs,event_loop_delay_ms:lag,api_response_count:requests,server_errors:errors,scope:'one authenticated desktop navigation during producer window; not all-module/mobile throughput certification'},null,2));
} finally {await browser.close();}
