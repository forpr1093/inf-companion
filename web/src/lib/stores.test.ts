import { expect, test } from "vitest";
import { get } from "svelte/store";
import { applyEvent, bindProgress, gifVersion } from "./stores";
import { DEFAULTS, emptyCounts, type ServerEvent } from "./events";

const hello = (extra: object): ServerEvent => ({
  type: "hello" as const, at: 0, version: "x", settings: DEFAULTS, devices: [], bindings: {},
  has_gif: true, counts: emptyCounts(), binding: null, gif_version: 0, screen: null, capture_status: { state: "off" }, ...extra,
}) as ServerEvent;

test("hello carries the gif version, so a page open across a restart reloads the GIF", () => {
  applyEvent(hello({ gif_version: 1700000000123 }));
  expect(get(gifVersion)).toBe(1700000000123);
});

test("hello restores a binding in progress", () => {
  applyEvent(hello({ binding: { target: "4", index: 3, total: 9 } }));
  expect(get(bindProgress)).toEqual({ target: "4", index: 3, total: 9 });
  applyEvent(hello({ binding: null }));
  expect(get(bindProgress)).toBeNull();
});

import { captureStatus, screen } from "./stores";

test("screen and capture status come from hello and live events", () => {
  applyEvent(hello({ screen: "music_select", capture_status: { state: "running" } }));
  expect(get(screen)).toBe("music_select");
  expect(get(captureStatus)).toEqual({ state: "running" });
  applyEvent({ type: "screen", at: 0, screen: "play" });
  applyEvent({ type: "capture_status", at: 0, state: "off", message: "tables missing" });
  expect(get(screen)).toBe("play");
  expect(get(captureStatus)).toEqual({ state: "off", message: "tables missing" });
});

import { nowPlaying, personalBest } from "./stores";

test("hello restores the chart and personal best; null leaves demo data alone", () => {
  nowPlaying.set(null); personalBest.set(null);
  const chart = { title: "Mermaid girl", artist: null, difficulty: "HYPER", level: 8, bpm: null, notes: 856 };
  const best = { score: 1437, notes: 856, lamp: "HARD CLEAR", miss_count: 8, last_played: null, source: "official" };
  applyEvent(hello({ chart, personal_best: best }));
  expect(get(nowPlaying)).toEqual(chart);
  expect(get(personalBest)).toEqual(best);
  applyEvent(hello({ chart: null, personal_best: null }));
  expect(get(nowPlaying)).toEqual(chart);
});

import { recentPlays } from "./stores";

test("hello restores recent plays; an empty list leaves demo data alone", () => {
  const play = { title: "Mermaid girl", difficulty: "HYPER", level: 8, score: 1228, notes: 856, option: null, played_at: "2026-11-27T12:00:00+00:00" };
  recentPlays.set([]);
  applyEvent(hello({ recent_plays: [play] }));
  expect(get(recentPlays)).toEqual([play]);
  applyEvent(hello({ recent_plays: [] }));
  expect(get(recentPlays)).toEqual([play]);
});
