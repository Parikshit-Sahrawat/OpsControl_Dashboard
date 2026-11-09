// Controlled design specimens only; no application configuration or provider calls.
import {mkdtemp,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const out=process.env.TYPE_OUT,url=process.env.TYPE_SPECIMEN_URL;
await mkdir(out,{recursive:true});const privateDir=await mkdtemp(tmpdir()+'/oc-type-browser-');
const report={status:'PENDING',kind:'DESIGN_ONLY_NOT_OWNER_ACCEPTANCE',cases:[],platformFonts:[],pageErrors:[],externalRequests:[],zoomKind:'CSS_ZOOM_EMULATION_NATIVE_BROWSER_ZOOM_BLOCKED',nativeZoom:'BLOCKED_EXTENSION_SERVICE_WORKER_UNAVAILABLE',fontBinariesCommitted:false};
let context;
try{
 const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE});
 context=await browser.newContext({viewport:{width:1440,height:900}});context._ownedBrowser=browser;
 const page=await context.newPage();page.on('pageerror',e=>report.pageErrors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(url))report.externalRequests.push(r.url());});
 async function zoom(z){await page.evaluate(value=>{document.documentElement.style.zoom=String(value);},z);}
 for(const font of ['baseline','inter','plex','source'])for(const theme of ['light','dark'])for(const [width,height] of [[1920,1080],[1440,900],[1366,768]]){
  await page.setViewportSize({width,height});await page.goto(`${url}/specimen.html?font=${font}&theme=${theme}`);await zoom(1);await page.evaluate(()=>document.fonts.ready);
  const metrics=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,font:getComputedStyle(document.querySelector('.page-title')).fontFamily,cls:window.typeMetrics.cls,heading:getComputedStyle(document.querySelector('.page-title')).fontSize,fonts:[...document.fonts].map(f=>({family:f.family,status:f.status}))}));assert(metrics.scrollWidth<=metrics.width,'Document has horizontal clipping');
  const cdp=await context.newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');const doc=await cdp.send('DOM.getDocument');const n=await cdp.send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'.page-title'});const actual=await cdp.send('CSS.getPlatformFontsForNode',{nodeId:n.nodeId});report.platformFonts.push({font,theme,width,fonts:actual.fonts});await cdp.detach();
  if(font!=='baseline')assert(actual.fonts.some(f=>f.isCustomFont),'Candidate font did not actually render');
  await page.screenshot({path:`${out}/${font}-${theme}-${width}x${height}.png`,fullPage:false});report.cases.push({font,theme,width,height,zoom:1,status:'PASS',metrics});
 }
 for(const theme of ['light','dark'])for(const z of [1,1.25,1.5,2]){
  await page.setViewportSize({width:1366,height:768});await page.goto(`${url}/specimen.html?font=plex&theme=${theme}`);await zoom(z);await page.evaluate(()=>document.fonts.ready);
  const widths=await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));assert(widths.document<=widths.viewport,'Zoom clipped document');
  const table=page.getByRole('region',{name:'Scrollable resource specimen table'});await table.focus();assert(await table.evaluate(e=>e===document.activeElement));await page.keyboard.press('ArrowRight');
  await page.screenshot({path:`${out}/plex-${theme}-zoom-${z}.png`,fullPage:false});report.cases.push({font:'plex',theme,width:1366,height:768,zoom:z,status:'PASS',widths,keyboardTableFocus:true});
 }
 await zoom(1);await page.setViewportSize({width:1920,height:1080});await page.goto(`${url}/specimen.html?font=plex`);await page.getByRole('button',{name:'Show three-font comparison'}).click();await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:out+'/three-candidate-comparison.png',fullPage:false});
 // Browser fallback corpus is recorded, not claimed as language certification.
 const fallback=await context.newCDPSession(page);await fallback.send('DOM.enable');await fallback.send('CSS.enable');const d=await fallback.send('DOM.getDocument');const n=await fallback.send('DOM.querySelector',{nodeId:d.root.nodeId,selector:'pre'});report.fallbackFonts=(await fallback.send('CSS.getPlatformFontsForNode',{nodeId:n.nodeId})).fonts;
 assert.equal(report.pageErrors.length,0);assert.equal(report.externalRequests.length,0);report.status='PARTIAL_DESIGN_SCOPE_NATIVE_BROWSER_ZOOM_BLOCKED';
}catch(e){report.status='FAIL';report.failure={type:e.name,message:e.message};throw e;}
finally{if(context){await context.close();await context._ownedBrowser.close();}await rm(privateDir,{recursive:true,force:true});report.privateProfileRemoved=true;await writeFile(out+'/RESULTS.json',JSON.stringify(report,null,2));}
