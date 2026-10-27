// D36: low-data mode plays the 32 kbps commentary and is saved on the device.
import { expect, test } from '@playwright/test';

test('low data: the switch is saved, and the commentary comes from the low-data folder', async ({ page }) => {
  await page.goto('/?view=setup');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  const box = page.getByRole('checkbox', { name: /Low data/ });
  await expect(box).not.toBeChecked();                                  // a fast test connection: off by default
  await box.check();
  await page.reload();
  await expect(page.getByRole('checkbox', { name: /Low data/ })).toBeChecked();
  const lo = page.waitForResponse((r) => r.url().includes('/audio/en/radio-lo/') && r.ok(), { timeout: 30_000 });
  await page.locator('#back-match').click();                         // D39: Settings, then the match
  await page.locator('#start').click();
  await lo;
});
