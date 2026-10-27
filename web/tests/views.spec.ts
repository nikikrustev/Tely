// D39 (27 Oct): one app in a laptop or a phone, three screens (match list, match, Settings), a match picked by voice,
// and the laptop keys (Space pauses, Enter asks). D25's tabs are now the two device tabs.
import { expect, test, type Page } from '@playwright/test';

/** A stand-in for the browser's SpeechRecognition that hears `said` (or nothing, or an error). */
async function fakeRecognition(page: Page, said: string | null, error?: string): Promise<void> {
  await page.addInitScript(([s, err]) => {
    (window as unknown as Record<string, unknown>).SpeechRecognition = class {
      onresult: ((e: unknown) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        setTimeout(() => {
          if (err) this.onerror?.({ error: err });
          else if (s !== null) this.onresult?.({ results: [[{ transcript: s }]] });
          this.onend?.();
        }, 100);
      }
      abort() {}
    };
  }, [said, error ?? null] as const);
}

test('the flow: match list, then the match, then Settings and back, without stopping the match', async ({ page }, info) => {
  await page.goto('/?view=phone');
  await expect(page.getByRole('heading', { name: 'Matches' })).toBeVisible();
  await expect(page.locator('#voice-pick')).toBeFocused();
  await expect(page.locator('#nav-home')).toHaveAttribute('aria-current', 'page');
  // One playable match and fictional fixtures, each marked as not in the demo.
  await expect(page.locator('#fixtures > li')).toHaveCount(5);
  await expect(page.locator('#fixtures button')).toHaveCount(1);
  await expect(page.locator('#fixtures li:not(:first-child)')).toContainText(Array(4).fill('Not available in the demo'));
  await expect(page.locator('#start')).toBeHidden();
  await page.getByRole('button', { name: /^Reds v Navy/ }).click();
  await expect(page.locator('#start')).toBeFocused();                 // the change of screen is a focus move
  await expect(page.locator('#status')).toHaveText(/^Reds against Navy\. Ready\./);
  // Nothing on the match screen but the bar and the two pads.
  for (const sel of ['#match', '#status']) await expect(page.locator(sel)).toHaveClass(/sr-only/);
  await expect(page.locator('#start-hint')).toHaveText('Starts the match');
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await page.getByRole('button', { name: 'Settings' }).click();
  await expect(page.locator('#setup-h')).toBeFocused();
  await expect(page.locator('#mixer')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('#settings')).toBeVisible();
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');      // changing screen never stops the match
  await page.getByRole('button', { name: 'Home: all matches' }).click();
  await expect(page.locator('#list-h')).toBeFocused();
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');
  await page.locator('#card-demo').click();
  await expect(page.locator('#start')).toHaveText('Pause');
  // The device is drawn only on a wide screen; on a phone-sized screen the app fills it and the device tabs go.
  const wide = info.project.name.startsWith('desktop');
  await expect(page.getByRole('tablist', { name: 'Device' })).toBeVisible({ visible: wide });
});

test('device tabs: Laptop and Phone, arrow keys between them, keys on Laptop and taps on Phone', async ({ page }, info) => {
  test.skip(!info.project.name.startsWith('desktop'), 'the device tabs show only where the device is drawn');
  await page.goto('/?view=laptop&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready\. Press Space/);
  await expect(page.getByRole('tablist', { name: 'Device' }).getByRole('tab')).toHaveText(['Laptop', 'Phone']);
  await expect(page.locator('#play-half .pad-key')).toHaveText('Space');        // the keys on the pads
  await expect(page.locator('#ask-half .pad-key')).toHaveText('Enter');
  await expect(page.locator('#play-half .pad-key')).toBeVisible();
  await expect(page.locator('#start-hint')).toHaveText('Press Space to start');
  await page.locator('#tab-laptop').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#tab-phone')).toBeFocused();
  await expect(page.locator('#tab-phone')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#view')).toHaveAttribute('aria-labelledby', 'tab-phone');
  await expect(page.locator('#play-half .pad-key')).toBeHidden();
  await expect(page.locator('#start-hint')).toHaveText('Starts the match');
  expect(page.url()).toContain('view=phone');
});

test('laptop keys: Space pauses and carries on, Enter asks', async ({ page }) => {
  await page.goto('/?view=laptop&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.keyboard.press('Enter');                                  // before the match: told how to start it
  await expect(page.locator('#status')).toHaveText("The match hasn't started. Press Space to start it.");
  await page.keyboard.press('Space');
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await expect(page.locator('#start-hint')).toHaveText('Press Space to pause');
  await expect(page.locator('#ask')).toHaveAttribute('aria-disabled', 'false', { timeout: 30_000 });
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());   // focus on nothing: the keys still work
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

test('Space and Enter do nothing to the match from the list', async ({ page }) => {
  await page.goto('/?view=laptop');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#list-h').focus();
  await page.keyboard.press('Space');
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-sb="state"]')).toHaveText('Not started');
  await expect(page.locator('#start')).toBeHidden();
});

test('voice: "Play Reds" pops the card up, and Enter opens the match', async ({ page }) => {
  await fakeRecognition(page, 'play reds');
  await page.goto('/?view=laptop');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#voice-pick').click();
  await expect(page.locator('#picked-open')).toBeVisible();
  await expect(page.locator('#picked-open')).toBeFocused();
  await expect(page.locator('#voice-status')).toHaveText('Reds against Navy. Press Enter to open the match.');
  await page.keyboard.press('Enter');
  await expect(page.locator('#start')).toBeFocused();
  await expect(page.locator('#picked')).toBeHidden();
});

test('voice: a fixture that is not in the demo, or no match, falls back to the list and says why', async ({ page }) => {
  await fakeRecognition(page, 'play saltmere');
  await page.goto('/?view=phone');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#voice-pick').click();
  await expect(page.locator('#voice-status')).toHaveText(/^Saltmere against Brackenmoor isn't available in the demo/);
  await expect(page.locator('#list-h')).toBeFocused();
  await expect(page.locator('li[data-fixture="saltmere"]')).toHaveAttribute('data-picked', '');
  await expect(page.locator('#picked')).toBeHidden();
});

test('voice: without speech recognition the list is the way in, and the page says so', async ({ page }) => {
  await page.addInitScript(() => {
    for (const k of ['SpeechRecognition', 'webkitSpeechRecognition']) delete (window as unknown as Record<string, unknown>)[k];
  });
  await page.goto('/?view=phone');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#voice-pick').click();
  await expect(page.locator('#voice-status')).toHaveText("Voice search isn't available in this browser. Pick a match from the list.");
  await expect(page.locator('#list-h')).toBeFocused();
});

test('Settings: the commentator language switches the commentary track and is kept on this device (D27)', async ({ page }) => {
  await page.goto('/?view=setup');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await expect(page.locator('#nav-settings')).toHaveAttribute('aria-current', 'page');
  const lang = page.getByLabel('Commentator language');
  await expect(lang).toHaveValue('en');
  const cues = page.waitForResponse((r) => r.url().endsWith('/cues.es.radio.jsonl'));
  await lang.selectOption('es');
  expect((await cues).ok()).toBe(true);
  await expect(page.locator('#status')).toHaveText('Commentary in Spanish.');
  await page.reload();
  await expect(page.getByLabel('Commentator language')).toHaveValue('es');
});
