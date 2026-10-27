// Listening-test clips (eval/listening_test.md) from the URL:
// ?from=&to= in playhead seconds (the contract `t`, as in the ?debug=1 panel), ?sound=commentary for the
// commentary-only clip: the voice alone, with no crowd, ball, earcons or vibration.
export interface ListenClip {
  from: number | null;
  to: number | null;
  commentaryOnly: boolean;
}

export function listenClip(search: string): ListenClip {
  const q = new URLSearchParams(search);
  const num = (k: string) => {
    const v = q.get(k);
    const n = v === null || v.trim() === '' ? NaN : Number(v);
    return Number.isFinite(n) && n >= 0 ? n : null;
  };
  const from = num('from');
  let to = num('to');
  if (from !== null && to !== null && to <= from) to = null;   // a reversed range plays on rather than stopping at once
  return { from, to, commentaryOnly: q.get('sound') === 'commentary' };
}

/** True once the playhead has reached the clip's end (never for an open-ended clip). */
export function clipOver(c: ListenClip, playheadS: number): boolean {
  return c.to !== null && playheadS >= c.to;
}
