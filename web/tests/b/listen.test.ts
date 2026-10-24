// OWNER: B lane (created by A, 24 Oct, Stage 8 item 6). The listening-test clip URLs in eval/listening_test.md.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { clipOver, listenClip } from '../../src/replay/listen';
import type { SegmentsDoc } from '../../src/replay/replay-source';

const J = new URL('../../public/replay/v1/judge/', import.meta.url);
const doc = JSON.parse(readFileSync(new URL('segments.json', J), 'utf8')) as SegmentsDoc;
const protocol = readFileSync(new URL('../../../eval/listening_test.md', import.meta.url), 'utf8');

describe('listening-test clips', () => {
  it('reads from, to and the commentary-only switch', () => {
    expect(listenClip('?from=670&to=850&sound=commentary')).toEqual({ from: 670, to: 850, commentaryOnly: true });
    expect(listenClip('?from=970&to=1150')).toEqual({ from: 970, to: 1150, commentaryOnly: false });
    expect(listenClip('')).toEqual({ from: null, to: null, commentaryOnly: false });
  });

  it('ignores bad values instead of stopping the match', () => {
    expect(listenClip('?from=abc&to=&sound=loud')).toEqual({ from: null, to: null, commentaryOnly: false });
    expect(listenClip('?from=900&to=800').to).toBeNull();
    expect(listenClip('?from=-5').from).toBeNull();
  });

  it('ends the clip at `to`, and an open clip never ends', () => {
    const c = listenClip('?from=670&to=850');
    expect([clipOver(c, 849.9), clipOver(c, 850)]).toEqual([false, true]);
    expect(clipOver(listenClip('?from=670'), 1e9)).toBe(false);
  });

  it('every clip URL in the protocol is a 3-minute window inside the judge cut', () => {
    const urls = [...protocol.matchAll(/https:\/\/\S+?(\?from=[^\s)`|]+)/g)].map((m) => m[1]!);
    expect(urls.length).toBeGreaterThanOrEqual(4);
    for (const u of urls) {
      const c = listenClip(u);
      expect(c.from).not.toBeNull();
      expect(c.to! - c.from!).toBe(180);
      expect(c.from!).toBeGreaterThanOrEqual(doc.t0);
      expect(c.to!).toBeLessThanOrEqual(doc.t1);
    }
  });
});
