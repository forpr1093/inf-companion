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
