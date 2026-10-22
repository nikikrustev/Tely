// OWNER: B (Nikolay). ?debug=1 panel: crowd gain, ball x and playhead, refreshed every animation frame.
// Visual only (aria-hidden): it is for checking the sound stage, not for listeners.
export interface DebugSource {
  playhead(): number;
  crowdGain(): number;
  ballX(): number;
}

export function formatDebug(s: DebugSource): string {
  // The playhead is seconds since the period started (contract `t`), not the match clock.
  return `playhead ${s.playhead().toFixed(1)} s  |  crowd gain ${s.crowdGain().toFixed(3)}  |  ball x ${s.ballX().toFixed(1)} m`;
}

export function startDebugPanel(el: HTMLElement, s: DebugSource): void {
  el.hidden = false;
  const tick = () => {
    el.textContent = formatDebug(s);
    requestAnimationFrame(tick);
  };
  tick();
}
