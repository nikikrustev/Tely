// D33: the Director's notes panel with ?radar=1, empty until a moment has played, and axe-clean.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test("Director's notes: shown with the radar, nothing before its moment, Ask traces added, no axe violations", async ({ page }) => {
  await page.goto('/?view=laptop&radar=1&live=0&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  const panel = page.getByRole('region', { name: "Director's notes" });
  await expect(panel).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('#notes-list li')).toHaveCount(0);          // the first chance is revealed at 56:43
  await page.evaluate(() => window.dispatchEvent(new CustomEvent('tely:ask-trace',
    { detail: { tools: ['get_score_and_clock'], latency_ms: 900 } })));
  await expect(page.locator('#notes-list li')).toHaveText([/Ask \(Voice Live\): get_score_and_clock; first answer audio 0\.90 s/]);
  for (const colorScheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme });
    const r = await new AxeBuilder({ page }).include('#notes').withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    expect(r.violations.map((v) => v.id), colorScheme).toEqual([]);
  }
});
