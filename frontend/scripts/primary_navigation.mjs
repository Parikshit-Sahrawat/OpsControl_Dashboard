// Use actual permission-filtered controls, never bypass navigation via application state.
export async function preparePrimaryNavigation(page) {
  await page.getByRole('button',{name:'Sign out',exact:true}).waitFor();
  const nav=page.getByRole('navigation',{name:'Primary navigation'});
  if(await nav.isHidden())await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await nav.waitFor();
  const toggles=nav.locator('button[aria-expanded][aria-label$=" navigation"]');
  for(let i=0;i<await toggles.count();i++){
    const toggle=toggles.nth(i);
    if(await toggle.getAttribute('aria-expanded')==='false')await toggle.click();
  }
  return nav;
}
export async function navigatePrimary(page,name){
  const nav=await preparePrimaryNavigation(page);
  const aliases={'Resource Management':['Data Sources / Resources'],'Access Management':['Employees'],'Data Pipeline Monitoring':['Data Pipeline Monitoring','Data Pipelines'],'Compute Health':['Compute Health','Compute Instances'],'API Endpoint Monitoring':['API Endpoint Monitoring','API Endpoints']};
  for(const label of aliases[name]||[name]){
    const target=nav.getByRole('button',{name:label,exact:true});
    if(await target.count()){await target.click();return;}
  }
  throw new Error('Approved navigation destination unavailable to authenticated user: '+name);
}
