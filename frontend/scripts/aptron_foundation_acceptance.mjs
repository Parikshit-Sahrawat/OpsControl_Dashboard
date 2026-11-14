// Called by the existing authenticated scope gate; no mocked authorization.
import assert from 'node:assert/strict';
import { join } from 'node:path';
import { writeFile } from 'node:fs/promises';

export async function checkFoundation(page, fixture, out) {
  const checks = [];
  const nav = page.getByRole('navigation', { name: 'Primary navigation' });
  const ui = process.env.V16_UI_URL;
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  assert.equal(await page.title(), 'APTron Observability');
  assert.match(await page.locator('.brand').innerText(), /APTron/);
  assert.equal(await nav.getByRole('button', { name: 'Incidents', exact: true }).count(), 0);
  checks.push('APTron title and header; excluded dedicated Incidents navigation absent');

  for (const [label, section] of [['Compute Instances', 'compute-instances'], ['Data Pipelines', 'data-pipelines'], ['APIs', 'apis']]) {
    await nav.getByRole('button', { name: label, exact: true }).click();
    await page.getByLabel('Resource Management component').waitFor();
    await page.waitForFunction(expected => document.querySelector('.resource-section-select select')?.value === expected, section);
    assert.equal(await page.getByLabel('Resource Management component').inputValue(), section);
    assert.ok(page.url().endsWith('#/resources/' + section));
    await page.reload();
    await page.getByLabel('Resource Management component').waitFor();
    await page.waitForFunction(expected => document.querySelector('.resource-section-select select')?.value === expected, section);
    assert.equal(await page.getByLabel('Resource Management component').inputValue(), section);
  }
  checks.push('Three domain inventory routes and reload retain the same guarded existing workspace');
  await page.goto(ui + '/#/pipelines/incidents');
  await page.getByRole('heading', { name: 'Pipeline Inventory', exact: true }).waitFor();
  assert.equal(await page.getByRole('link', { name: 'Incident Correlation', exact: true }).count(), 0);
  checks.push('Retired pipeline incident bookmark cannot reopen dedicated incident management');

  for (const mode of ['light', 'dark']) {
    await page.getByRole('button', { name: mode === 'light' ? 'Light theme' : 'Dark theme', exact: true }).click();
    for (const width of [1366, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      const help = page.getByRole('button', { name: 'Help', exact: true });
      await help.click();
      const dialog = page.getByRole('dialog', { name: 'Help and operator guides' });
      await dialog.waitFor();
      for (const name of ['Documentation', 'Learning', 'Training'])
        await dialog.getByRole('heading', { name, exact: true }).waitFor();
      const links = await dialog.getByRole('link').all();
      assert.equal(links.length, 3);
      for (const link of links) {
        const url = new URL(await link.getAttribute('href'), ui);
        assert.equal(url.origin, new URL(ui).origin);
        const response = await page.request.get(url.href);
        assert.equal(response.status(), 200);
        assert.match(await response.text(), /^# APTron Observability/);
      }
      const box = await dialog.boundingBox();
      assert.ok(box.x >= 0 && box.x + box.width <= width + 1);
      assert.ok(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1));
      // The first/last focusable controls include FAQ summaries.
      await dialog.getByRole('button', { name: 'Close personal workspace' }).focus();
      await page.keyboard.press('Shift+Tab');
      assert.equal(await dialog.locator('summary').last().evaluate(el => el === document.activeElement), true);
      await page.keyboard.press('Tab');
      assert.equal(await dialog.getByRole('button', { name: 'Close personal workspace' }).evaluate(el => el === document.activeElement), true);
      await page.screenshot({ path: join(out, `aptron-help-${mode}-${width}.png`), fullPage: true });
      await page.keyboard.press('Escape');
      assert.equal(await dialog.count(), 0);
      assert.equal(await help.evaluate(el => el === document.activeElement), true);
    }
  }
  checks.push('Help: three locally shipped guides, responsive light/dark containment, FAQ keyboard trap, Escape and focus restoration');
  await page.setViewportSize({ width: 1366, height: 900 });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.getByRole('heading', { name: 'APTron Observability', exact: true }).waitFor();
  await page.getByLabel('Username', { exact: true }).fill('v16-api-viewer');
  await page.getByLabel('Password', { exact: true }).fill(fixture.viewer_password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await nav.waitFor();
  const principal = await page.evaluate(async api => {
    const response = await fetch(api + '/api/v1/auth/me', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('opscontrol.sessionToken') } });
    if (!response.ok) throw new Error('Cannot read authenticated viewer authority');
    return response.json();
  }, fixture.base_url);
  if (!principal.permissions.includes('access.view'))
    assert.equal(await nav.getByRole('group', { name: 'Access Management', exact: true }).count(), 0);
  assert.equal(await nav.getByRole('button', { name: 'Incidents', exact: true }).count(), 0);
  await page.getByRole('button', { name: 'Help', exact: true }).click();
  await page.getByRole('heading', { name: 'Training', exact: true }).waitFor();
  await page.keyboard.press('Escape');
  await page.screenshot({ path: join(out, 'aptron-viewer-navigation.png'), fullPage: true });
  checks.push('Real viewer receives role-filtered navigation and customer self-hosted Help');
  assert.deepEqual(errors, []);
  await writeFile(join(out, 'aptron-foundation-browser.json'), JSON.stringify({ status: 'PASS', checks, limitations: ['Keyboard/name/viewport checks; not comprehensive WCAG or assistive-technology certification', 'Controlled fixtures; not scheduler/native Collector certification'] }, null, 2));
}
