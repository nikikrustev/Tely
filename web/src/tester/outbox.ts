// Tester mode (?test=1, D19): getting each event to the relay's POST /feedback.
// fetch with keepalive (it survives the tab closing) and one retry after 30 s, because the relay scales to zero and
// its cold start is over 30 s (D17). If both tries fail, the event stays saved as "unsent": the thank-you screen
// offers "Copy my answers", and the next visit tries again. An answer is never thrown away.

export const RETRY_AFTER_MS = 30_000;

export interface Transport {
  /** POST the body; resolves with the HTTP status, rejects on a network error. */
  post(url: string, body: string): Promise<number>;
  wait(ms: number): Promise<void>;
}

export type Delivery = 'sent' | 'unsent';

export async function deliver(url: string | null, body: string, t: Transport): Promise<Delivery> {
  if (!url) return 'unsent';
  for (let attempt = 0; attempt < 2; attempt++) {
    if (attempt === 1) await t.wait(RETRY_AFTER_MS);
    try {
      const status = await t.post(url, body);
      if (status >= 200 && status < 300) return 'sent';
      if (status === 400 || status === 403 || status === 413) return 'unsent';   // a retry would get the same answer
    } catch {
      // network error or a cold relay: try once more after the wait
    }
  }
  return 'unsent';
}

/** The browser transport. text/plain keeps it a CORS "simple" request, so keepalive needs no preflight. */
export const browserTransport: Transport = {
  async post(url, body) {
    const r = await fetch(url, { method: 'POST', body, keepalive: true, mode: 'cors', credentials: 'omit',
      headers: { 'content-type': 'text/plain;charset=UTF-8' } });
    return r.status;
  },
  wait: (ms) => new Promise((r) => setTimeout(r, ms)),
};

/** The relay's /feedback URL from its /voice URL (voice/index.ts liveRelayUrl), or null without a relay. */
export function feedbackUrl(voiceUrl: string | null): string | null {
  return voiceUrl ? voiceUrl.replace(/^ws/, 'http').replace(/\/voice$/, '/feedback') : null;
}
