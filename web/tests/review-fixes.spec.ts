// The 27 Oct review (a55ab1a): bugs a judge could hit in the page, one test each.
import { expect, test } from '@playwright/test';

test('full time: the replay stops, Ask works without looping, and Space replays from the start (item 1)', async ({ page }) => {
  await page.goto('/?view=laptop&live=0&from=1146&screen=match');   // 4 s before the end of the judge cut (t1 = 1150)
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#start').click();
  // The end recap plays first, then full time.
  await expect(page.locator('#status')).toHaveText(/^Full time\. Press Space/, { timeout: 50_000 });
  await expect(page.locator('#start .pad-label')).toHaveText('Replay from the start');
  await expect(page.locator('#start-hint')).toHaveText('Press Space to replay from the start');
  await expect(page.locator('[data-sb="state"]')).toHaveText('Full time');
  // Before the fix, Enter here looped (resume, ask, resume...) and never opened anything.
  await page.keyboard.press('Enter');
  await expect(page.locator('#ask-menu')).toBeVisible();
  await page.getByRole('button', { name: "What's the score?" }).click();
  await expect(page.locator('#status')).toHaveText(/Navy/, { timeout: 15_000 });
  await expect(page.locator('#ask')).toHaveAttribute('data-state', 'ask', { timeout: 20_000 });
  await expect(page.locator('#start .pad-label')).toHaveText('Replay from the start');   // still full time
  await page.locator('#ask').focus();
  await page.keyboard.press(' ');
  await expect(page.locator('#status')).toHaveText('Playing from the start.');
  await expect(page.locator('#start')).toHaveText('Pause');
  await expect(page.locator('[data-sb="clock"]')).not.toHaveText(/^9[0-9]/);
});

test('a failed Start can be pressed again (item 5)', async ({ page }) => {
  let fail = true;
  await page.route('**/segments.json', (route) => (fail ? route.abort() : route.continue()));
  await page.goto('/?view=laptop&live=0&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#start').click();
  await expect(page.locator('#status')).toHaveText("Couldn't load the match. Press Start to try again.", { timeout: 30_000 });
  await expect(page.locator('#start')).toBeEnabled();
  fail = false;
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');
});

test('"Next big moment" during an answer stops the answer before the jump (item 6)', async ({ page }) => {
  await page.goto('/?view=laptop&live=0&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready/);           // a press before the page is wired is lost
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  await page.locator('#nav-settings').click();                       // D39: these live in Settings
  await page.locator('#presets-open').click();
  await page.getByRole('button', { name: 'Recap so far' }).click();
  await expect(page.locator('#ask')).toHaveAttribute('data-state', 'stop');
  await page.locator('#nav-settings').click();                       // mid-answer, as a fan might
  await page.locator('#next').click();
  await expect(page.locator('#ask')).toHaveAttribute('data-state', 'ask');   // the answer was stopped, not left running
  await expect(page.locator('#status')).not.toHaveText(/story so far|Answering/);
  await expect(page.locator('[data-sb="state"]')).toHaveText('Playing');
});

test('"Learn the sounds" and a quick Space make one stage AudioContext, not two (item 8)', async ({ page }) => {
  // The stage's context is the one main.ts adds the Setup desk's analyser to (the voice has two of its own).
  await page.addInitScript(() => {
    const stages = new Set<BaseAudioContext>();
    (window as unknown as { stageCount: () => number }).stageCount = () => stages.size;
    const make = AudioContext.prototype.createAnalyser;
    AudioContext.prototype.createAnalyser = function (this: AudioContext) { stages.add(this); return make.call(this); };
  });
  await page.goto('/?view=laptop&live=0&screen=match');
  await expect(page.locator('#status')).toHaveText(/Ready/);
  await page.locator('#nav-settings').click();                       // D39: these live in Settings
  await page.locator('#learn').click();
  await page.locator('#back-match').click();
  await page.locator('#start').click();
  await expect(page.locator('#start')).toHaveText('Pause', { timeout: 30_000 });
  expect(await page.evaluate(() => (window as unknown as { stageCount: () => number }).stageCount())).toBe(1);
});
