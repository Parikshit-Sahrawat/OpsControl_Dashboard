import http from 'node:http';
import {chromium} from '/tmp/oc-closure-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const rows=[],errors=[];process.on('unhandledRejection',e=>errors.push(String(e)));
const server=http.createServer((req,res)=>{res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Access-Control-Allow-Headers','Content-Type,X-Probe');res.setHeader('Access-Control-Max-Age','0');res.setHeader('Content-Type','application/json');res.end(JSON.stringify({method:req.method,status:'fixture'}));});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const url=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true,executablePath:'/tmp/oc-etl003a-browsers/chromium-1194/chrome-linux/chrome'});const page=await browser.newPage();await page.goto(url);
try{for(let i=0;i<40 && !errors.length;i++){
 let release;const gate=new Promise(r=>release=r);let pending=0;const events=[];
 await page.route('**/configuration-context',async route=>{pending++;const event={method:route.request().method()};events.push(event);try{const response=await route.fetch();event.fetched=true;await gate;await route.fulfill({response});event.fulfilled=true;}catch(e){event.error=String(e);errors.push(String(e));throw e;}finally{pending--;}});
 await page.evaluate(u=>{window.probe=[];for(let n=0;n<2;n++) {let c=new AbortController();window.probe.push(fetch(u+'/configuration-context',{headers:{'Content-Type':'application/json','X-Probe':'synthetic'},signal:c.signal}).then(r=>r.json()).catch(e=>({error:e.name})));if(n===0)queueMicrotask(()=>c.abort());}},url.replace('127.0.0.1','localhost'));
 for(let n=0;n<50 && !events.some(e=>e.fetched);n++)await new Promise(r=>setTimeout(r,5));
 release();await page.unrouteAll({behavior:'wait'});await page.evaluate(()=>Promise.all(window.probe));rows.push({iteration:i,events,pending});
}}finally{await browser.close();await new Promise(r=>server.close(r));fs.writeFileSync('/tmp/oc-s1-ci006/route-repro.json',JSON.stringify({rows,errors},null,2));}
console.log(JSON.stringify({iterations:rows.length,errors},null,2));
