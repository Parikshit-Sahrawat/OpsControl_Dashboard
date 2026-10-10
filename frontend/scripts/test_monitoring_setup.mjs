import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const browser=await chromium.launch({headless:true});
const page=await browser.newPage({viewport:{width:1366,height:900}});
const errors=[];
page.on("pageerror",error=>errors.push(String(error)));
try{
  await page.goto("http://127.0.0.1:5173",{waitUntil:"domcontentloaded"});
  await page.getByRole("textbox",{name:"Username"}).fill("test-admin");
  await page.getByLabel("Password").fill("testing-only-StrongPassword-123!");
  await page.getByRole("button",{name:"Sign in"}).click();
  await page.getByRole("button",{name:"Monitoring Setup"}).waitFor();
  await page.getByRole("button",{name:"Monitoring Setup"}).click();
  await page.getByRole("heading",{name:"Monitoring Setup"}).waitFor();
  await page.getByText("Select a Data Source and private-network worker").waitFor();
  await page.getByText("Choose independent Metric, Log and Alert Rules").waitFor();
  await page.getByRole("button",{name:"Validate & Preview"}).waitFor();
  await page.getByRole("button",{name:"Save immutable rule v1"}).waitFor();
  await page.getByRole("button",{name:"Create worker and network policy"}).waitFor();
  await mkdir("phase1-screenshots",{recursive:true});
  await page.screenshot({path:"phase1-screenshots/monitoring-setup-real.png",fullPage:true});
  if(errors.length) throw new Error(errors.join("; "));
  console.log("MONITORING SETUP AUTHENTICATED UI SMOKE PASSED");
}finally{await browser.close();}
