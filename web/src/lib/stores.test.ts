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
