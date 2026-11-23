import { expect, test } from "vitest";
import { get } from "svelte/store";
import { applyKey, counterTarget, emptyCounts } from "./counts";
import { applyEvent, counts } from "../stores";
import { DEFAULTS, type KeyEvent, type Lane } from "../events";

const down = (lane: Lane, dir: KeyEvent["dir"] = null): KeyEvent => ({ type: "key_down", lane, dir, t: 0, at: 0 });
const up = (lane: Lane, dir: KeyEvent["dir"] = null): KeyEvent => ({ type: "key_up", lane, dir, t: 0, at: 0 });

test("key downs count, ups don't, scratch split by direction", () => {
  let c = emptyCounts();
  for (const e of [down("1"), up("1"), down("1"), down("S", "up"), down("S", "down"), up("S", "down")]) c = applyKey(c, e);
  expect(c).toMatchObject({ "1": 2, S_up: 1, S_down: 1, "2": 0 });
});

test("applyKey returns a new object", () => {
  const c = emptyCounts();
  expect(applyKey(c, down("3"))).not.toBe(c);
  expect(c["3"]).toBe(0);
});

test("counter target", () => {
  expect(counterTarget(down("S", "down"))).toBe("S_down");
  expect(counterTarget(down("S", "up"))).toBe("S_up");
  expect(counterTarget(down("7"))).toBe("7");
});

test("hello replaces local counts", () => {
  for (let i = 0; i < 3; i++) applyEvent(down("5"));
  expect(get(counts)["5"]).toBe(3);
  applyEvent({ type: "hello", at: 0, version: "x", settings: DEFAULTS, devices: [], bindings: {}, has_gif: false, counts: emptyCounts(), binding: null, gif_version: 0, screen: null, capture_status: { state: "off" } });
  expect(get(counts)["5"]).toBe(0);
  applyEvent(down("5"));
  applyEvent({ type: "counts", at: 0, counts: { ...emptyCounts(), "2": 9 } });
  expect(get(counts)).toMatchObject({ "5": 0, "2": 9 });
});
