// web/staticwebapp.config.json: the headers Static Web Apps sends with every file (27 Oct review, item 8).
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const cfg = JSON.parse(readFileSync(new URL('../staticwebapp.config.json', import.meta.url), 'utf-8')) as {
  globalHeaders: Record<string, string>;
};

describe('static headers', () => {
  it('only this site may use the mic (live Ask), and no other site can frame the page', () => {
    expect(cfg.globalHeaders['Permissions-Policy']).toMatch(/(^|, )microphone=\(self\)/);
    expect(cfg.globalHeaders['Content-Security-Policy']).toContain("frame-ancestors 'none'");
    expect(cfg.globalHeaders['X-Content-Type-Options']).toBe('nosniff');
  });
});
