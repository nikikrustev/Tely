// OWNER: A (potencialbg). Tier 1 item 7 (D31): "Recap so far" in the quick questions, spoken from verified pieces.
import { expect, test } from '@playwright/test';

test('Recap so far: a quick question that tells the story up to now, and nothing after it', async ({ page }) => {
  await page.goto('/?view=laptop&live=0');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await page.locator('#presets-open').click();
  const recap = page.getByRole('button', { name: 'Recap so far' });
  await expect(recap).toBeVisible();
  await recap.click();
  await expect(page.locator('#status')).toHaveText(/^Here's the story so far\. Reds nil, Navy nil, 56 minutes played\. Nothing big has happened yet\./,
    { timeout: 15_000 });
});
