import { expect, test } from "vitest";
import { fitContain, frameAt, loopRate, normaliseDelays, phaseKeepingStart } from "./rate";

test("loop lasts beatsPerLoop beats", () => {
  expect(loopRate(120, 4, 2000)).toBeCloseTo(1);    // 4 beats at 120 bpm = 2000 ms
  expect(loopRate(240, 4, 2000)).toBeCloseTo(2);
  expect(loopRate(150, 2, 1000)).toBeCloseTo(1.25);
});

test("zero delays treated as 100 ms", () => {
  expect(normaliseDelays([0, 10, 20])).toEqual([100, 100, 20]);
  expect(Number.isFinite(loopRate(150, 4, normaliseDelays([0, 0]).reduce((a, b) => a + b)))).toBe(true);
});

test("frameAt loops and scales", () => {
  expect(frameAt(0, [100, 100], 1)).toBe(0); expect(frameAt(150, [100, 100], 1)).toBe(1);
  expect(frameAt(250, [100, 100], 1)).toBe(0); expect(frameAt(75, [100, 100], 2)).toBe(1);
});

test("changing rate keeps the loop phase", () => {
  // At now=1000 with start=0 and rate 1 over a 400 ms loop, phase is 1000 % 400 = 200.
  const start2 = phaseKeepingStart(1000, 0, 1, 2, 400);
  expect(((1000 - start2) * 2) % 400).toBeCloseTo(200);
});

test("fitContain keeps aspect inside the cell", () => {
  expect(fitContain(100, 50, 200, 200)).toEqual({ x: 0, y: 50, w: 200, h: 100 });
  expect(fitContain(50, 100, 200, 100)).toEqual({ x: 75, y: 0, w: 50, h: 100 });
});

import { gifPlan } from "./rate";

test("small GIFs are kept at full size", () => {
  expect(gifPlan(8, 160, 160)).toEqual({ ok: true, scale: 1 });
});

test("big GIFs are stored smaller so memory stays bounded", () => {
  const p = gifPlan(400, 800, 450);           // 144 M pixels decoded
  expect(p.ok).toBe(true);
  if (p.ok) {
    expect(p.scale).toBeLessThan(0.5);
    expect(400 * 800 * 450 * p.scale * p.scale).toBeLessThanOrEqual(24_000_000 + 1);
  }
});

test("wide GIFs are capped to 640 px on their long side", () => {
  const p = gifPlan(2, 1280, 720);
  expect(p).toEqual({ ok: true, scale: 0.5 });
});

test("GIFs too large to decode are refused with a plain reason", () => {
  const p = gifPlan(200, 1920, 1080);         // 414 M pixels
  expect(p.ok).toBe(false);
  if (!p.ok) expect(p.reason).toBe("This GIF is too large (200 frames at 1920×1080). Try a shorter or smaller one.");
});
