// OWNER: B lane (written by A after the 24 Oct handover). BUILD_PLAN Stage 8 item 4: Playwright + @axe-core/playwright
// on every screen a fan meets: Start, the Ask menu, Settings, the sound radar (?radar=1) and "Learn the sounds".
// Each runs at 3 viewports, with and without reduced motion (playwright.config.ts projects), in light and dark.
// WHY the extra checks at the end: file 32 §6, axe can't see live-region setup, target size of hidden-then-shown
// controls or running animations, so we assert those ourselves.
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

/** Scan the page as it is now, in light and dark, and fail with a readable list of what axe found. */
async function expectNoViolations(page: Page, label: string): Promise<void> {
  for (const colorScheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme });
    const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    const found = r.violations.map((v) => `${v.id} (${v.impact}): ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`);
    expect(found, `axe on ${label}, ${colorScheme}`).toEqual([]);
  }
}

async function ready(page: Page, url = '/'): Promise<void> {
  await page.goto(url);
  await expect(page.locator('#status')).toHaveText(/Ready/);
}

async function startMatch(page: Page): Promise<void> {
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
}

test('Start screen', async ({ page }) => {
  await ready(page);
  await expectNoViolations(page, 'Start');
});

test('Ask menu', async ({ page }) => {
  await ready(page);
  await startMatch(page);
  const ask = page.locator('#ask');
  await expect(ask).toBeEnabled({ timeout: 30_000 });
  await ask.click();
  await expect(page.locator('#ask-menu')).toBeVisible();
  await expect(ask).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#ask-menu button[data-preset]').first()).toBeFocused();
  await expectNoViolations(page, 'Ask menu');
});

test('Settings', async ({ page }) => {
  await ready(page);
  await page.locator('#settings-toggle').click();
  await expect(page.locator('#settings')).toBeVisible();
  await expect(page.locator('#settings-toggle')).toHaveAttribute('aria-expanded', 'true');
  await expectNoViolations(page, 'Settings');
});

test('sound radar (?radar=1)', async ({ page }) => {
  await ready(page, '/?radar=1');
  await startMatch(page);
  const radar = page.locator('#radar');
  await expect(radar).toBeVisible();
  await expect(radar).toHaveAttribute('aria-hidden', 'true');   // the listener hears all of it
  await expect(radar.locator('canvas')).toHaveCount(1);
  await expectNoViolations(page, 'radar');
});

test('Learn the sounds', async ({ page }) => {
  await ready(page);
  const learn = page.locator('#learn');
  await learn.click();
  await expect(learn).toHaveText('Skip the tour', { timeout: 30_000 });
  await expectNoViolations(page, 'Learn the sounds');
  await page.keyboard.press('Escape');
  await expect(learn).toHaveText('Learn the sounds again', { timeout: 15_000 });
  await expect(page.locator('#start')).toBeFocused();
});

test('what axe cannot see: live regions, target size, motion', async ({ page }, info) => {
  await ready(page);
  // Live regions exist and are empty at load (MDN: a region must pre-exist to be announced; WCAG 4.1.3).
  await expect(page.locator('#sr-polite')).toHaveAttribute('role', 'status');
  await expect(page.locator('[aria-live="assertive"]')).toHaveCount(1);
  await expect(page.locator('#sr-assertive')).toHaveText('');
  // WCAG 2.5.8 floor is 24 px; index.html aims for 44 px on every control, including those Settings reveals.
  await page.locator('#settings-toggle').click();
  for (const el of await page.locator('button:visible, select:visible, input[type="range"]:visible').all()) {
    const box = await el.boundingBox();
    expect(box, await el.evaluate((e) => e.outerHTML.slice(0, 80))).not.toBeNull();
    expect(Math.round(box!.height)).toBeGreaterThanOrEqual(44);
    expect(Math.round(box!.width)).toBeGreaterThanOrEqual(44);
  }
  // WCAG 1.4.10: no horizontal scroll at any of our viewports (320 CSS px reflow is the portrait phone's case).
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  // Reduced motion: nothing animates (the radar redraws twice a second instead; radar.ts).
  if (info.project.use.reducedMotion === 'reduce') {
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);
  }
});
