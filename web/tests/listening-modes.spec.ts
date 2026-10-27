// Tier 1 items 5 and 6 (D30) in a real browser, with axe (WCAG 2.2 AA) on the new controls.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

test('Setup: detail level and the two listening modes are labelled, saved on this device, and pass axe', async ({ page }) => {
  await page.goto('/?view=setup');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await expect(page.getByRole('group', { name: 'How much the commentator says' })).toBeVisible();
  const full = page.getByRole('radio', { name: /Full radio/ }), key = page.getByRole('radio', { name: /Key moments only/ });
  await expect(full).toBeChecked();
  await key.check();
  await expect(page.locator('#status')).toHaveText('Key moments only.');
  const reader = page.getByRole('checkbox', { name: /Screen-reader mode/ }), mono = page.getByRole('checkbox', { name: /One ear/ });
  await reader.check();
  await expect(page.locator('#status')).toHaveText(/Screen-reader mode on/);
  await mono.check();
  await expect(page.locator('#status')).toHaveText(/One ear mode on/);
  for (const colorScheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme });
    const r = await new AxeBuilder({ page }).include('#settings').withTags(TAGS).analyze();
    expect(r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`), colorScheme).toEqual([]);
  }
  await page.reload();
  await expect(page.getByRole('radio', { name: /Key moments only/ })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: /Screen-reader mode/ })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: /One ear/ })).toBeChecked();
});

test('screen-reader mode: each commentary line goes to a polite live region instead of the AI voice', async ({ page }) => {
  await page.goto('/?view=setup');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  const region = page.locator('#reader-lines');
  await expect(region).toHaveAttribute('aria-live', 'polite');
  await expect(region).toBeEmpty();
  await page.getByRole('checkbox', { name: /Screen-reader mode/ }).check();
  await page.locator('#back-match').click();                         // D39: Settings, then the match
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await expect(region).toHaveText('AI commentary, synthetic match.', { timeout: 20_000 });   // the first line, on time
  await expect(region).toHaveAttribute('lang', 'en');
});
