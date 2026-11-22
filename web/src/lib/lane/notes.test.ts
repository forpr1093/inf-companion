import { expect, test } from "vitest";
import { NoteField } from "./notes";

test("tap note rises and fades out", () => {
  const f = new NoteField({ riseMs: 1000 });
  f.press("1", 0); f.release("1", 50);
  const n = f.frame(550)[0]; expect(n.bottom).toBeCloseTo(0.5); expect(n.alpha).toBe(1);
  expect(f.frame(900)[0].alpha).toBeLessThan(1); expect(f.frame(2100)).toEqual([]);
});

test("held note grows from the judge line", () => {
  const f = new NoteField({ riseMs: 1000 }); f.press("S", 0);
  const n = f.frame(300)[0]; expect(n.bottom).toBe(0); expect(n.top).toBeCloseTo(0.3);
});

test("hold length is capped at the lane height", () => {
  const f = new NoteField({ riseMs: 1000 }); f.press("S", 0);
  const n = f.frame(5000)[0]; expect(n.top - n.bottom).toBeCloseTo(1);
});

test("rapid presses each spawn a note", () => {
  const f = new NoteField({ riseMs: 2000 });
  for (let i = 0; i < 30; i++) { f.press("4", i * 40); f.release("4", i * 40 + 10); }
  expect(f.frame(30 * 40).filter(n => n.lane === "4").length).toBe(30);
});

test("releaseAll on reset ends held notes", () => {
  const f = new NoteField({ riseMs: 1000 });
  f.press("1", 0); f.press("S", 0);
  f.releaseAll(100);
  const ns = f.frame(300);
  expect(ns.length).toBe(2);
  expect(ns.every(n => n.bottom > 0)).toBe(true);
});

test("release without press is ignored and maxNotes drops oldest", () => {
  const f = new NoteField({ maxNotes: 3 });
  f.release("2", 0);
  for (let i = 0; i < 5; i++) { f.press("1", i); f.release("1", i); }
  expect(f.frame(5).length).toBe(3);
});

test("press flash fades over 120 ms", () => {
  const f = new NoteField(); f.press("3", 0);
  expect(f.flashes(0)[0]).toEqual({ lane: "3", alpha: 1 });
  expect(f.flashes(60)[0].alpha).toBeCloseTo(0.5);
  expect(f.flashes(130)).toEqual([]);
});
