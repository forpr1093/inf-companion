import { expect, test } from "vitest";
import { get } from "svelte/store";
import { applyEvent, bindProgress, gifVersion } from "./stores";
import { DEFAULTS, emptyCounts } from "./events";

const hello = (extra: object) => ({
  type: "hello" as const, at: 0, version: "x", settings: DEFAULTS, devices: [], bindings: {},
  has_gif: true, counts: emptyCounts(), binding: null, gif_version: 0, ...extra,
});

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
