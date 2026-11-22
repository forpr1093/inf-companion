import { afterEach, expect, test, vi } from "vitest";
import { devKeyboardMap, startDemo } from "./demo";
import type { KeyEvent } from "./events";

afterEach(() => vi.useRealTimers());

test("demo is deterministic and balanced", () => {
  vi.useFakeTimers();
  const a: KeyEvent[] = [], b: KeyEvent[] = [];
  const stopA = startDemo(e => a.push(e), { seed: 1, bpm: 150 }); vi.advanceTimersByTime(4000); stopA();
  const stopB = startDemo(e => b.push(e), { seed: 1, bpm: 150 }); vi.advanceTimersByTime(4000); stopB();
  expect(a.length).toBeGreaterThan(20);
  expect(a.map(e => [e.type, e.lane, e.dir])).toEqual(b.map(e => [e.type, e.lane, e.dir]));
  expect(a.filter(e => e.type === "key_down").length).toBe(a.filter(e => e.type === "key_up").length);
});

test("demo includes scratch with a direction", () => {
  vi.useFakeTimers();
  const a: KeyEvent[] = [];
  const stop = startDemo(e => a.push(e), { seed: 7, bpm: 180 }); vi.advanceTimersByTime(8000); stop();
  const s = a.filter(e => e.lane === "S" && e.type === "key_down");
  expect(s.length).toBeGreaterThan(0);
  expect(s.every(e => e.dir === "up" || e.dir === "down")).toBe(true);
  expect(a.filter(e => e.lane !== "S").every(e => e.dir === null)).toBe(true);
});

test("dev keyboard map covers every lane", () => {
  expect(new Set(Object.values(devKeyboardMap).map(v => v.lane))).toEqual(new Set(["S", "1", "2", "3", "4", "5", "6", "7"]));
});
