// OWNER: A (potencialbg). The ?mix=1 sound mixer, Playwright + axe at the 3 viewports, light and dark. Also proves
// the judges' page has no mixer without ?mix=1.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

test('no mixer on the judges\' page', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#start')).toBeFocused();
  await expect(page.locator('#mixer')).toHaveCount(0);
});

test('the mixer: a labelled slider per group, Reset, Submit, no axe violations, 44 px targets', async ({ page }) => {
  await page.goto('/?mix=1');
  await expect(page.locator('#m-h')).toBeVisible({ timeout: 30_000 });
  for (const id of ['crowdBeds', 'chants', 'roars', 'pass', 'shot', 'whistle', 'commentator', 'nearEnd']) {
    await expect(page.locator(`#m-${id}`)).toBeVisible();
  }
  await expect(page.locator('input[name="m-pos"]')).toHaveCount(3);
  // D24: the helper explanation comes before the sliders, and the mix is kept on this device across visits.
  await expect(page.locator('#m-helper')).toContainText('sighted friend or carer');
  await page.locator('#m-pass').fill('-20');
  await expect(page.locator('output[for="m-pass"]')).toHaveText('-20.0 dB');
  await expect(page.locator('#m-saved')).toHaveText('Saved on this device.');
  await page.reload();
  await expect(page.locator('output[for="m-pass"]')).toHaveText('-20.0 dB', { timeout: 30_000 });
  await page.locator('#m-reset').click();
  await expect(page.locator('output[for="m-pass"]')).not.toHaveText('-20.0 dB');
  const download = page.waitForEvent('download');
  await page.locator('#m-submit').click();
  expect((await download).suggestedFilename()).toBe('audio-mix.json');
  await expect(page.locator('#m-json')).toBeVisible();
  expect(JSON.parse(await page.locator('#m-json').inputValue()).version).toBe(1);
  for (const colorScheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme });
    const r = await new AxeBuilder({ page }).include('#mixer').withTags(TAGS).analyze();
    expect(r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
  }
  for (const el of await page.locator('#mixer :is(button, input[type="range"]):visible').all()) {
    const box = await el.boundingBox();
    expect(Math.round(box!.height)).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
