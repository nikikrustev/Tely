// OWNER: B lane (created by A, 24 Oct, Stage 8 item 4). Playwright + axe accessibility tests in tests/b/*.spec.ts.
// WHY a preview build and not `vite dev`: CI checks the same static files Static Web Apps serves (file 21), and the
// build needs no keys (live Ask is off without /live.json, so the page falls back to presets).
// Run locally with `npm run test:a11y` (builds, serves on :4173, runs every project).
import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;
// file 32 §6: desktop, phone portrait and phone landscape (the judge opens the link on a phone).
const VIEWPORTS = {
  desktop: { width: 1280, height: 720 },
  portrait: { width: 390, height: 844 },
  landscape: { width: 844, height: 390 },
};

export default defineConfig({
  testDir: 'tests',
  testMatch: '**/*.spec.ts',            // vitest owns *.test.ts; these never collide
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  timeout: 60_000,
  use: {
    baseURL: process.env.A11Y_BASE_URL ?? `http://localhost:${PORT}`,
    trace: 'retain-on-failure',
    launchOptions: { args: ['--autoplay-policy=no-user-gesture-required'] },
  },
  // Every viewport twice: the OS default and prefers-reduced-motion: reduce.
  projects: Object.entries(VIEWPORTS).flatMap(([name, viewport]) =>
    (['no-preference', 'reduce'] as const).map((reducedMotion) => ({
      name: reducedMotion === 'reduce' ? `${name}-reduced-motion` : name,
      use: { ...devices['Desktop Chrome'], viewport, reducedMotion },
    }))),
  // A11Y_BASE_URL points the tests at a deployed site instead (no local server then).
  webServer: process.env.A11Y_BASE_URL ? undefined : {
    command: `npm run build && npx vite preview --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
