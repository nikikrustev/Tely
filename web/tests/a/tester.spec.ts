// OWNER: A (potencialbg). Tester mode (?test=1, D19), Playwright + axe at the 3 viewports (playwright.config.ts),
// light and dark. Also proves the judges' page is untouched without ?test=1: no tester markup, no tester code
// loaded, Start still focused. The preview build has no /live.json, so no relay: every answer stays "unsent" and
// the thank-you screen must offer "Copy my answers" (never lose an answer). With A11Y_BASE_URL (the deployed site)
// the relay answers instead, and those two checks flip; note those runs send real events to App Insights.
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const LIVE = !!process.env.A11Y_BASE_URL;
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

async function expectNoViolations(page: Page, label: string): Promise<void> {
  for (const colorScheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme });
    const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    const found = r.violations.map((v) => `${v.id} (${v.impact}): ${v.help}\n  ${v.nodes.map((n) => n.target.join(' ')).join('\n  ')}`);
    expect(found, `axe on ${label}, ${colorScheme}`).toEqual([]);
  }
}

/** Every visible control is at least 44 x 44 px and nothing scrolls sideways (WCAG 2.5.5 aim, 1.4.10). */
async function expectTargetsAndReflow(page: Page): Promise<void> {
  for (const el of await page.locator('button:visible, select:visible, input[type="range"]:visible, textarea:visible').all()) {
    const box = await el.boundingBox();
    expect(box, await el.evaluate((e) => e.outerHTML.slice(0, 80))).not.toBeNull();
    expect(Math.round(box!.height)).toBeGreaterThanOrEqual(44);
    expect(Math.round(box!.width)).toBeGreaterThanOrEqual(44);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

async function welcome(page: Page): Promise<void> {
  await page.goto('/?test=1');
  await expect(page.locator('#t-welcome-h')).toBeFocused({ timeout: 30_000 });
}

async function begin(page: Page): Promise<void> {
  await welcome(page);
  await page.locator('#t-take-part').check();
  await page.locator('#t-begin').click();
  await expect(page.locator('#t-tasks-h')).toBeFocused();
}

test('without ?test=1 the judges\' page is unchanged', async ({ page }) => {
  const testerCode: string[] = [];
  page.on('request', (r) => { if (/\/tester\//.test(r.url())) testerCode.push(r.url()); });
  await page.goto('/');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await expect(page.locator('#start')).toBeFocused();
  for (const sel of ['#tester', '#t-bar', '#t-report', '[id^="t-"]']) await expect(page.locator(sel)).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.classList.contains('t-mode'))).toBe(false);
  // The template is there but inert: nothing from it is in the tab order or the accessibility tree.
  await expect(page.getByRole('button', { name: /Report a problem/ })).toHaveCount(0);
  await page.keyboard.press('f');                                    // F does nothing on the judges' page
  await expect(page.locator('dialog')).toHaveCount(0);
  expect(testerCode).toEqual([]);
});

test('tester mode: welcome and consent', async ({ page }) => {
  await welcome(page);
  await expect(page.locator('#start')).toBeHidden();                 // the app waits behind the welcome
  await expect(page.getByRole('button', { name: 'Report a problem (F)' })).toBeVisible();
  // No name, email or age is ever asked for: the only inputs are checkboxes, radios and optional text areas.
  await expect(page.locator('#tester input:not([type="checkbox"]):not([type="radio"])')).toHaveCount(0);
  await page.locator('#t-begin').click();                            // without "take part": a plain message, focus on the box
  await expect(page.locator('#t-consent-err')).toBeVisible();
  await expect(page.locator('#t-take-part')).toBeFocused();
  await expectNoViolations(page, 'tester welcome');
  await expectTargetsAndReflow(page);
});

test('tester mode: task list', async ({ page }) => {
  await begin(page);
  await expect(page.locator('#t-list > li')).toHaveCount(8);
  await expect(page.getByRole('button', { name: 'Start this task: Clip 1, eyes closed' })).toBeVisible();
  await expect(page.locator('#t-progress')).toHaveText(/0 of 8 tasks finished\. About 15 minutes left\./);
  // The condition never shows: not in the URL, not on screen.
  expect(page.url()).not.toMatch(/sound=|from=|to=/);
  await expect(page.locator('body')).not.toContainText(/commentary only|full sound|group [AB]/i);
  await expectNoViolations(page, 'tester task list');
  await expectTargetsAndReflow(page);
});

test('tester mode: clip task and questions, by keyboard only', async ({ page }) => {
  await begin(page);
  await page.getByRole('button', { name: 'Start this task: Clip 1, eyes closed' }).press('Enter');
  await expect(page.locator('#t-task-h')).toBeFocused();
  await expect(page.locator('#t-task-h')).toHaveText('Task 2 of 8: Clip 1, eyes closed');
  await expectNoViolations(page, 'tester clip task');
  await page.getByRole('button', { name: 'Skip this task' }).press('Enter');
  await expect(page.locator('#sr-polite')).toHaveText('Task 2 skipped. Next: Questions about clip 1.');
  await expect(page.getByRole('button', { name: 'Start this task: Questions about clip 1' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#t-task-h')).toHaveText('Task 3 of 8: Questions about clip 1');
  await expect(page.locator('#t-form fieldset')).toHaveCount(7);
  for (const fs of await page.locator('#t-form fieldset').all()) await expect(fs.getByRole('radio', { name: "Don't know" }).or(fs.getByRole('radio', { name: /^1,/ }))).toHaveCount(1);
  await expectNoViolations(page, 'tester questions');
  await expectTargetsAndReflow(page);
  // Sending with nothing answered stops on the first question (native validation).
  await page.getByRole('button', { name: 'Send my answers' }).press('Enter');
  await expect(page.locator('#t-form input[name="p_where"]').first()).toBeFocused();
  // Answer every question from the keyboard: focus lands on a group's first radio, arrows move, Space picks.
  await page.keyboard.press('ArrowDown');                            // where: "Close to the goal at the right end"
  for (const name of ['p_side', 'p_danger', 'p_scored', 's_enjoy', 's_access', 's_follow']) {
    await page.keyboard.press('Tab');
    await expect(page.locator(`#t-form input[name="${name}"]`).first()).toBeFocused();
    await page.keyboard.press('Space');
  }
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Send my answers' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#sr-polite')).toHaveText(/Task 3 done\. Next: Clip 2, eyes closed\./);
  // Saved locally even with no relay, scored but never shown.
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('audiostands.tester.v1') ?? '{}'));
  const clipEv = saved.events.find((e: { ev: { kind: string } }) => e.ev.kind === 'clip');
  expect(clipEv.ev).toMatchObject({ clip: 1, where: 'right_close', where_ok: 0, enjoy: 1 });
  if (!LIVE) expect(clipEv.status).not.toBe('sent');   // with the relay (deployed site) it is sent
  await expect(page.locator('body')).not.toContainText(/where_ok|out of 4|correct/i);
});

test('tester mode: report a problem (button and F key)', async ({ page }) => {
  await begin(page);
  await page.keyboard.press('f');
  const dialog = page.getByRole('dialog', { name: 'Report a problem' });
  await expect(dialog).toBeVisible();
  await expectNoViolations(page, 'report dialog');
  await expectTargetsAndReflow(page);
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await page.getByRole('button', { name: 'Report a problem (F)' }).click();
  await dialog.getByRole('radio', { name: 'It crashed or got stuck' }).check();
  await dialog.getByLabel('Tell us more (optional)').fill('It stopped after the goal');
  await dialog.getByRole('button', { name: 'Send' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.locator('#sr-polite')).toHaveText(/Your report is saved/);
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('audiostands.tester.v1') ?? '{}'));
  const ev = saved.events.find((e: { ev: { kind: string } }) => e.ev.kind === 'problem').ev;
  expect(ev).toMatchObject({ problem_kind: 'stuck', problem_text: 'It stopped after the goal', ctx_task: 0, ctx_relay: LIVE,
    ctx_club: 'H', ctx_browser: 'chrome' });
  expect(ev.ctx_viewport).toMatch(/^\d+x\d+$/);
  expect(JSON.stringify(ev)).not.toMatch(/Mozilla|HeadlessChrome/);  // the user agent family only
});

test('tester mode: overall feedback and the thank-you screen keep every answer', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await begin(page);
  await page.getByRole('button', { name: 'Start this task: Overall feedback' }).click();
  await expect(page.locator('#t-task-h')).toHaveText('Task 8 of 8: Overall feedback');
  await expectNoViolations(page, 'overall feedback');
  await expectTargetsAndReflow(page);
  await page.getByLabel('What did you like?').fill('Хареса ми тълпата');
  await page.getByRole('radio', { name: 'Clip 2' }).check();
  await page.getByRole('button', { name: 'Send my answers' }).click();
  await page.getByRole('button', { name: "I'm finished" }).click();
  await expect(page.locator('#t-thanks-h')).toBeFocused();
  await expect(page.locator('#t-sent')).toHaveText(LIVE ? /have reached us|Still sending/ : /not reached us yet|Still sending/);
  await expect(page.locator('#t-mail')).toBeHidden();                // no address configured yet
  await expectNoViolations(page, 'thank-you');
  await expectTargetsAndReflow(page);
  await page.getByRole('button', { name: 'Copy my answers' }).click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('What did you like? Хареса ми тълпата');
  expect(copied).toContain('Preferred clip: Clip 2');
  expect(copied).toMatch(/AS1\.[A-Za-z0-9+/=]+$/);
});

test('tester mode: works when storage throws', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('denied', 'SecurityError'); } });
  });
  await begin(page);
  await page.getByRole('button', { name: 'Skip: Learn the sounds' }).click();
  await expect(page.locator('#sr-polite')).toHaveText('Task 1 skipped. Next: Clip 1, eyes closed.');
});
