// Actual browser forms and authenticated backend; no mocked API responses.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href);
const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE });
const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
const errors = [], serverErrors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('response', r => { if (r.url().includes('/api/') && r.status() >= 500) serverErrors.push(r.status()); });
const base = process.env.TEST_API_BASE;
const password = 'testing-only-StrongPassword-123!';
let phase = 'login';
try {
  await page.goto(process.env.RELEASE_UI_BASE);
  await page.getByLabel('Username').fill('test-north');
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('heading', { name: 'Overview', exact: true }).waitFor();
  phase = 'open onboarding';
  await page.getByRole('button', { name: 'Resource Management', exact: true }).click();
  await page.getByRole('button', { name: '+ Add Data Source', exact: true }).click();
  let modal = page.getByRole('dialog', { name: 'Add Data Source', exact: true });
  await modal.getByRole('button', { name: 'Next: Data Source →' }).click();
  await modal.getByLabel('Host Name', { exact: true }).fill('wizard-sequence.example.test');
  await modal.getByLabel('Visible Name', { exact: true }).fill('Wizard sequence registration');
  await modal.getByRole('button', { name: 'Next: Templates →' }).click();
  await modal.getByRole('button', { name: 'Next: Agent & Collector →' }).click();
  await modal.getByLabel('Agent / Collector Name', { exact: true }).fill('wizard-registration');
  await modal.getByLabel('Agent Version', { exact: true }).fill('1.0-synthetic');
  await modal.getByRole('button', { name: 'Review →' }).click();
  await modal.getByRole('button', { name: 'Create Data Source + Agent Configuration', exact: true }).click();
  phase = 'locate created resource';
  await modal.waitFor({ state: 'hidden' });
  await page.locator('.resource-summary-card').filter({ hasText: 'Data Sources' }).click();
  let row = page.getByRole('row').filter({ hasText: 'Wizard sequence registration' });
  await row.waitFor();
  const token = await page.evaluate(() => sessionStorage.getItem('opscontrol.sessionToken'));
  const headers = { Authorization: 'Bearer ' + token };
  const sourcesResponse = await page.request.get(base + '/api/v1/resource-management/data-sources', { headers });
  assert.equal(sourcesResponse.status(), 200);
  const source = (await sourcesResponse.json()).find(s => s.name === 'wizard-sequence.example.test');
  assert.ok(source);
  const collectorPath = base + '/api/v1/resource-management/collectors?data_source_id=' + source.id;
  let registrations = await (await page.request.get(collectorPath, { headers })).json();
  assert.equal(registrations.length, 1);
  const registration = registrations[0];
  assert.equal(registration.collector_type, 'OTEL');
  assert.equal(registration.enabled, false);
  assert.equal(registration.status, 'STOPPED');
  assert.equal(registration.configuration.agent.version, '1.0-synthetic');
  const duplicate = await page.request.post(base + '/api/v1/resource-management/data-sources', {
    headers, data: { organization_id: source.organization_id, name: source.name, source_type: source.source_type },
  });
  assert.equal(duplicate.status(), 409);
  phase = 'edit registration';
  await row.getByRole('button', { name: 'Edit', exact: true }).click();
  modal = page.getByRole('dialog', { name: 'Edit Data Source', exact: true });
  await modal.getByRole('button', { name: 'Next: Data Source →' }).click();
  await modal.getByRole('button', { name: 'Next: Templates →' }).click();
  await modal.getByRole('button', { name: 'Next: Agent & Collector →' }).click();
  assert.equal(await modal.getByLabel('Agent Version', { exact: true }).inputValue(), '1.0-synthetic');
  await modal.getByLabel('Agent Version', { exact: true }).fill('2.0-synthetic');
  await modal.getByRole('button', { name: 'Review →' }).click();
  await modal.getByRole('button', { name: 'Save Data Source', exact: true }).click();
  phase = 'verify persisted registration';
  await modal.waitFor({ state: 'hidden' });
  registrations = await (await page.request.get(collectorPath, { headers })).json();
  assert.equal(registrations.length, 1);
  assert.equal(registrations[0].id, registration.id);
  assert.equal(registrations[0].configuration.agent.version, '2.0-synthetic');
  assert.equal(registrations[0].enabled, false);
  const runs = await page.request.get(base + '/api/v1/monitoring/collectors/' + registration.id + '/runs', { headers });
  assert.deepEqual(await runs.json(), []);
  const otherLogin = await page.request.post(base + '/api/v1/auth/login', { data: { username: 'test-south', password } });
  assert.equal(otherLogin.status(), 200);
  const otherHeaders = { Authorization: 'Bearer ' + (await otherLogin.json()).access_token };
  const cross = await page.request.patch(base + '/api/v1/resource-management/data-sources/' + source.id, {
    headers: otherHeaders, data: { name: 'forged-cross-tenant' },
  });
  assert.equal(cross.status(), 404);
  const crossRows = await page.request.get(collectorPath, { headers: otherHeaders });
  assert.deepEqual(await crossRows.json(), []);
  await mkdir(process.env.RELEASE_EVIDENCE_DIR, { recursive: true });
  await page.screenshot({ path: process.env.RELEASE_EVIDENCE_DIR + '/resource-registration.png', fullPage: true });
  phase = 'disable resource';
  page.once('dialog', dialog => dialog.accept());
  row = page.getByRole('row').filter({ hasText: 'Wizard sequence registration' });
  await row.getByRole('button', { name: 'Disable', exact: true }).click();
  await row.getByRole('button', { name: 'Disable', exact: true }).waitFor({ state: 'hidden' });
  const disabled = (await (await page.request.get(base + '/api/v1/resource-management/data-sources', { headers })).json()).find(s => s.id === source.id);
  assert.equal(disabled.enabled, false);
  assert.deepEqual(errors, []); assert.deepEqual(serverErrors, []);
  await writeFile(process.env.RELEASE_EVIDENCE_DIR + '/resource-crud.json', JSON.stringify({ status: 'PASS',
    checks: ['Browser create/read/update/disable persisted', 'Duplicate source returns 409',
      'OTEL registration stays inactive with no CollectorRun', 'Edit preserves ID and updates stored agent settings',
      'Other tenant cannot read registration or mutate source'], page_errors: errors, server_errors: serverErrors }, null, 2));
  console.log('RESOURCE WIZARD / INACTIVE REGISTRATION / CRUD / TENANT ACCEPTANCE PASS');
} catch (error) {
  // Only a fixture phase and error type leave the private diagnostics directory.
  console.error('RESOURCE_CRUD_FAILURE ' + JSON.stringify({ phase, type: error.name }));
  throw error;
} finally { await browser.close(); }
