export const jobs = [
  { id:"JH-000842", jobOrderId:"JO-000127", name:"JC_Pricing_Daily", server:"HERO-PRDAPP001", environment:"PROD", executionType:"SCHEDULED", start:"08:00:01", end:"08:05:49", duration:"05m 48s", expectedRuntime:"20m", sla:"30m", status:"FAILED", failedStep:"Update Customer Database", error:"Connection timeout", incident:"INC0012345", lastSuccessful:"06-Oct 08:00", lastFailed:"07-Oct 08:04" },
  { id:"JH-000843", jobOrderId:"JO-000128", name:"Job_SPP_PAI", server:"HERO-PRDAPP001", environment:"PROD", executionType:"SCHEDULED", start:"08:15:02", end:null, duration:"18m 12s", expectedRuntime:"15m", sla:"30m", status:"RUNNING", failedStep:null, error:null, incident:null, lastSuccessful:"07-Oct 08:15", lastFailed:"30-Sep 08:16" },
  { id:"JH-000844", jobOrderId:"JO-000129", name:"Customer_Extract", server:"ETL-PRD-02", environment:"PROD", executionType:"SCHEDULED", start:"07:00:00", end:null, duration:"24m 01s", expectedRuntime:"20m", sla:"25m", status:"LONG_RUNNING", failedStep:null, error:null, incident:"INC0012339", lastSuccessful:"07-Oct 07:00", lastFailed:"01-Oct 07:00" },
  { id:"JH-000845", jobOrderId:"JO-000130", name:"Inventory_Daily", server:"ETL-PRD-03", environment:"PROD", executionType:"SCHEDULED", start:"06:30:01", end:"06:47:34", duration:"17m 33s", expectedRuntime:"20m", sla:"30m", status:"SUCCESS", failedStep:null, error:null, incident:null, lastSuccessful:"08-Oct 06:47", lastFailed:"02-Oct 06:31" },
  { id:"JH-000846", jobOrderId:"JO-000131", name:"Customer_Reconciliation", server:"ETL-PRD-04", environment:"PROD", executionType:"SCHEDULED", start:null, end:null, duration:null, expectedRuntime:"15m", sla:"30m", status:"NO_RUN", failedStep:null, error:null, incident:"INC0012348", expectedWindow:"08:00-08:15", gracePeriod:"15m", lastSuccessful:"07-Oct 08:13", lastFailed:"01-Oct 08:02" },
  { id:"JH-000847", jobOrderId:"JO-000132", name:"Inventory_Replay", server:"ETL-QA-01", environment:"QA", executionType:"MANUAL", start:"09:10:02", end:"09:17:11", duration:"07m 09s", expectedRuntime:"10m", sla:"20m", status:"SUCCESS", failedStep:null, error:null, incident:null, lastSuccessful:"08-Oct 09:17", lastFailed:"—" },
];

const commonHistory = [
  {time:"07-Oct 08:04",status:"FAILED",reason:"Database timeout",incident:"INC0012291"},
  {time:"06-Oct 08:00",status:"SUCCESS",duration:"18m"},
  {time:"05-Oct 08:00",status:"SUCCESS",duration:"19m"},
];

export const jobDetails = {
  "JH-000842": {
    organization:"ABC Corporation", pentahoInstance:"PENTAHO-PROD-01", detected:"08:05:55 IST", lastUpdate:"08:18:00 IST",
    slaStatus:"BREACHED", failureCategory:"Database", suspectedCause:"Database listener unavailable", confidence:"HIGH",
    relatedHealth:{Database:"UNAVAILABLE",CPU:"87%",RAM:"61%",Network:"HEALTHY",Tomcat:"HEALTHY"},
    steps:[
      {name:"Extract Customer Data",status:"SUCCESS",type:"Table Input",duration:"01m 11s"},
      {name:"Transform Pricing",status:"SUCCESS",type:"Transformation",duration:"03m 09s"},
      {name:"Update Customer Database",status:"FAILED",type:"Table Output",duration:"00m 01s"},
      {name:"Generate Output",status:"NOT_STARTED",type:"Text File Output"},
    ],
    timeline:[
      {time:"08:00:01",event:"Job started",source:"Pentaho"},
      {time:"08:01:12",event:"Extract started",source:"Pentaho"},
      {time:"08:04:21",event:"Transformation started",source:"Pentaho"},
      {time:"08:05:48",event:"Database connection error",source:"Pentaho"},
      {time:"08:05:49",event:"Job failed",source:"Pentaho"},
      {time:"08:05:55",event:"OpsControl detected failure",source:"OpsControl"},
      {time:"08:06:01",event:"PagerDuty triggered",source:"PagerDuty"},
      {time:"08:06:05",event:"ServiceNow incident created",source:"ServiceNow"},
    ],
    incidentHistory:[
      {time:"08:05:55",event:"Failure detected",reference:"CRITICAL"},
      {time:"08:06:01",event:"PagerDuty triggered",reference:"PD-12345"},
      {time:"08:06:05",event:"ServiceNow incident created",reference:"INC0012345"},
      {time:"08:06:07",event:"Email notification sent",reference:"SLM Operations"},
      {time:"08:08:14",event:"PagerDuty acknowledged",reference:"Operator A"},
    ],
    recentHistory:commonHistory,
    investigation:{status:"INVESTIGATING",operator:"Operator A",started:"08:08:14 IST",notes:[
      {timestamp:"08:08",operator:"Operator A",text:"Acknowledged alert and started investigation."},
      {timestamp:"08:10",operator:"Operator A",text:"Database team contacted."},
      {timestamp:"08:18",operator:"Operator A",text:"DB listener appears unavailable. Waiting for DB team confirmation."},
    ],transitions:[
      {previous:"NEW",next:"ACKNOWLEDGED",timestamp:"08:08:14 IST",operator:"Operator A"},
      {previous:"ACKNOWLEDGED",next:"INVESTIGATING",timestamp:"08:10:00 IST",operator:"Operator A"},
    ]},
  },
  "JH-000843": {
    organization:"ABC Corporation",pentahoInstance:"PENTAHO-PROD-01",detected:"08:15:07 IST",lastUpdate:"08:33:14 IST",slaStatus:"ON TRACK",
    steps:[{name:"Extract Data",status:"SUCCESS",type:"Table Input",duration:"06m"},{name:"Transform",status:"RUNNING",type:"Transformation"}],
    timeline:[{time:"08:15:02",event:"Job started",source:"Pentaho"},{time:"08:15:07",event:"Execution detected",source:"OpsControl"},{time:"08:21:02",event:"Transform started",source:"Pentaho"}],
    incidentHistory:[],recentHistory:[{time:"07-Oct 08:15",status:"SUCCESS",duration:"14m"}],
  },
  "JH-000844": {
    organization:"ABC Corporation",pentahoInstance:"PENTAHO-PROD-02",detected:"07:00:05 IST",lastUpdate:"07:24:01 IST",slaStatus:"AT RISK",
    steps:[{name:"Extract Inventory",status:"SUCCESS",duration:"08m"},{name:"Transform Inventory",status:"RUNNING",duration:"15m"}],
    timeline:[{time:"07:00:00",event:"Job started",source:"Pentaho"},{time:"07:20:00",event:"Expected runtime exceeded",source:"OpsControl"}],
    incidentHistory:[{time:"07:20:05",event:"Long-running alert",reference:"INC0012339"}],recentHistory:[{time:"07-Oct 07:00",status:"SUCCESS",duration:"19m"}],
    investigation:{status:"ACKNOWLEDGED",operator:"Operator B",started:"07:20:05 IST",notes:[],transitions:[{previous:"NEW",next:"ACKNOWLEDGED",timestamp:"07:20:05 IST",operator:"Operator B"}]},
  },
  "JH-000846": {
    organization:"ABC Corporation",pentahoInstance:"PENTAHO-PROD-02",detected:"08:15:02 IST",lastUpdate:"08:15:02 IST",slaStatus:"NOT MET",
    expectedWindow:"08:00-08:15",gracePeriod:"15m",steps:[],timeline:[{time:"08:15:00",event:"Expected execution window ended",source:"OpsControl"},{time:"08:30:00",event:"No-run grace period exceeded",source:"OpsControl"}],
    incidentHistory:[{time:"08:30:01",event:"No-run alert",reference:"INC0012348"}],recentHistory:[{time:"07-Oct 08:13",status:"SUCCESS",duration:"13m"}],
    investigation:{status:"NEW",operator:"—",started:"08:30:01 IST",notes:[],transitions:[]},
  },
};