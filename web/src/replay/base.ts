// OWNER: A (potencialbg; B's lane since the 24 Oct handover). Where the replay bundle lives. Always the judge cut,
// except `?bundle=<stem>` on the dev server: the full-length soak bundles (D24, pipeline/audiostands/eval/
// soak_bundle.py) in git-ignored web/.local/, which only `vite dev` serves. On the deployed site that path 404s.
export const JUDGE_BASE = '/replay/v1/judge';

export function bundleBase(search: string = typeof location === 'undefined' ? '' : location.search): string {
  const stem = new URLSearchParams(search).get('bundle');
  return stem && /^[a-z0-9-]{1,40}$/.test(stem) ? `/replay/v1/local/${stem}` : JUDGE_BASE;
}
