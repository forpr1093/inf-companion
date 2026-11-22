import { expect, test } from "vitest";
import { get } from "svelte/store";
import { DIFF_SHORT, djBorder, djLevel } from "./score";
import { applyEvent, nowPlaying, personalBest, recentPlays } from "./stores";

// notes 1000 -> max 2000; lines: E 445, D 667, C 889, B 1112, A 1334, AA 1556, AAA 1778
test("dj level", () => {
  expect(djLevel(2000, 1000)).toBe("AAA"); expect(djLevel(1777, 1000)).toBe("AA");
  expect(djLevel(444, 1000)).toBe("F"); expect(djLevel(445, 1000)).toBe("E");
});

test("nearest border label", () => {
  expect(djBorder(1600, 1000)!.label).toBe("AA+44");
  expect(djBorder(1700, 1000)!.label).toBe("AAA−78");
  expect(djBorder(367, 1000)!.label).toBe("E−78");
  expect(djBorder(1556, 1000)!.label).toBe("AA+0");
  expect(djBorder(1445, 1000)).toEqual({ level: "A", diff: 111, label: "A+111" });
  expect(djBorder(100, null)).toBeNull();
});

test("tie goes to the line at or below the score", () => {
  // notes 9 -> max 18: A line 12, AA line 14; 13 is 1 from each.
  expect(djBorder(13, 9)!.label).toBe("A+1");
});

test("difficulty short names", () => {
  expect(DIFF_SHORT.LEGGENDARIA).toBe("L"); expect(DIFF_SHORT.ANOTHER).toBe("A");
});

test("panel events land in stores", () => {
  const chart = { title: "Sample", difficulty: "ANOTHER" as const, level: 12, bpm: 175, notes: 1500 };
  applyEvent({ type: "chart", at: 0, chart });
  expect(get(nowPlaying)).toEqual(chart);
  applyEvent({ type: "personal_best", at: 0, best: null });
  expect(get(personalBest)).toBeNull();
  const play = { title: "Sample", difficulty: "HYPER" as const, level: 10, score: 1800, notes: 1000, option: "RANDOM", played_at: "2026-11-23T10:00:00Z" };
  applyEvent({ type: "recent_plays", at: 0, plays: [play] });
  expect(get(recentPlays)).toEqual([play]);
  applyEvent({ type: "chart", at: 0, chart: null });
  expect(get(nowPlaying)).toBeNull();
});
