// D34: "Follow a player" in Setup lists every player, is saved, and passes axe.
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('Follow a player: every player in the list, the choice is saved, no axe violations', async ({ page }) => {
  await page.goto('/?view=setup');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  const sel = page.getByLabel('Follow a player');
  await expect(sel.locator('option')).toHaveCount(23);              // Nobody + 22 players
  await sel.selectOption('n11');                                     // Jude Olvholm (#11)
  await expect(page.locator('#status')).toHaveText(/^Following .*Olvholm\.$/);
  const r = await new AxeBuilder({ page }).include('#settings').withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(r.violations.map((v) => v.id)).toEqual([]);
  await page.reload();
  await expect(page.getByLabel('Follow a player')).not.toHaveValue('');
});
