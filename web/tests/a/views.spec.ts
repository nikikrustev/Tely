// OWNER: A (potencialbg). D25 (27 Oct): three tabs over one match, and the laptop keys (Space pauses, Enter asks).
import { expect, test } from '@playwright/test';

test('three tabs switch the layout, not the match, and arrow keys move between them', async ({ page }) => {
  await page.goto('/?view=laptop');
  await expect(page.locator('#status')).toHaveText(/Ready\. Press Space/);
  await expect(page.locator('#keys')).toBeVisible();
  await expect(page.getByRole('tablist', { name: 'View' }).getByRole('tab')).toHaveText(['Setup', 'Laptop', 'Phone']);
  await expect(page.locator('#start-hint')).toHaveText('Press Space to start');
  await page.locator('#tab-laptop').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#tab-phone')).toBeFocused();
  await expect(page.locator('#tab-phone')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#view')).toHaveAttribute('aria-labelledby', 'tab-phone');
  await expect(page.locator('#keys')).toBeHidden();
  await expect(page.locator('#start-hint')).toHaveText('Starts the match');
  expect(page.url()).toContain('view=phone');
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await page.locator('#tab-setup').click();
  await expect(page.locator('#mixer')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');      // switching views never stops the match
  await expect(page.locator('#settings')).toBeVisible();
  await page.locator('#tab-laptop').click();
  await expect(page.locator('#settings')).toBeHidden();
  await expect(page.locator('#mixer')).toBeHidden();
});

test('laptop keys: Space pauses and carries on, Enter asks', async ({ page }) => {
  await page.goto('/?view=laptop');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.keyboard.press('Enter');                                  // before the match: told how to start it
  await expect(page.locator('#status')).toHaveText("The match hasn't started. Press Space to start it.");
  await page.keyboard.press('Space');
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await expect(page.locator('#start-hint')).toHaveText('Press Space to pause');
  await expect(page.locator('#ask')).toHaveAttribute('aria-disabled', 'false', { timeout: 30_000 });
  await page.locator('body').click({ position: { x: 5, y: 5 } });      // focus on nothing: the keys still work
  await page.keyboard.press('Space');
  await expect(page.locator('[data-sb="state"]')).toHaveText('Paused');
  await page.keyboard.press('Space');
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');
  await page.locator('#start').focus();                                // Enter on the Start pad still asks
  await page.keyboard.press('Enter');
  if (process.env.A11Y_BASE_URL) await expect(page.locator('#ask')).toHaveText('Stop the answer');   // live Ask
  else await expect(page.locator('#ask-menu')).toBeVisible();          // no relay: the quick questions
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');
});
