// GIF timing: play one loop in `beatsPerLoop` beats of the current BPM.

/** Browsers treat frame delays of 0 or 1 centisecond as 100 ms. */
export function normaliseDelays(delaysMs: number[]): number[] {
  return delaysMs.map(d => (d <= 10 ? 100 : d));
}

/** Speed multiplier so the GIF's own loop lasts beatsPerLoop beats at bpm. */
export function loopRate(bpm: number, beatsPerLoop: number, gifDurationMs: number): number {
  const targetMs = (beatsPerLoop * 60000) / bpm;
  return gifDurationMs / targetMs;
}

/** Frame index at `elapsedMs` of wall time, playing at `rate`, looping. */
export function frameAt(elapsedMs: number, delaysMs: number[], rate: number): number {
  const total = delaysMs.reduce((a, b) => a + b, 0);
  if (total <= 0) return 0;
  let t = ((elapsedMs * rate) % total + total) % total;
  for (let i = 0; i < delaysMs.length; i++) {
    if (t < delaysMs[i]) return i;
    t -= delaysMs[i];
  }
  return delaysMs.length - 1;
}

/** New start time so the loop phase stays put when the rate changes (no jump). */
export function phaseKeepingStart(now: number, start: number, oldRate: number, newRate: number, loopMs: number): number {
  const phase = (((now - start) * oldRate) % loopMs + loopMs) % loopMs;
  return now - phase / newRate;
}

/** Fit a w×h image inside a cell, centred, without stretching. */
export function fitContain(w: number, h: number, cellW: number, cellH: number): { x: number; y: number; w: number; h: number } {
  const s = Math.min(cellW / w, cellH / h);
  const dw = w * s, dh = h * s;
  return { x: (cellW - dw) / 2, y: (cellH - dh) / 2, w: dw, h: dh };
}
