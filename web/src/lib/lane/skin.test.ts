import { expect, test } from "vitest";
import { DEFAULTS, type Lane } from "../events";
import { frameGeometry, loadSkin, skinUrls, spriteKind } from "./skin";

test("skin urls follow settings", () => {
  const u = skinUrls({ ...DEFAULTS, skin_notes: "pastel", skin_frame: "fancy_purple" });
  expect(u.notes).toBe("/skin/play/parts/notes/pastel.png?dir=skins%2FWMII_FHD");
  expect(u.frame).toBe("/skin/play/parts/frame/Wide/fancy_purple.png?dir=skins%2FWMII_FHD");
  expect(u.beam).toBe("/skin/play/parts/laser/defalut.png?dir=skins%2FWMII_FHD");
  expect(u.turntable).toBe("/skin/play/parts/turntable/simpleBlue_whiteLine.png?dir=skins%2FWMII_FHD");
});

test("sprite kind per lane", () => {
  expect(["S", "1", "2", "7"].map(l => spriteKind(l as Lane))).toEqual(["s", "w", "b", "w"]);
});

test("frame geometry per side, scaled", () => {
  const g1 = frameGeometry("1P", 685), g2 = frameGeometry("2P", 342.5);
  expect(g1.laneX).toBe(75); expect(g1.judgeY).toBe(793); expect(g1.laneW).toBe(576);
  expect(g2.laneX).toBeCloseTo(17.5); expect(g2.judgeY).toBeCloseTo(396.5);
  expect(g1.disc).toEqual({ x: 65, y: 803, size: 123 });
  expect(g2.disc.x).toBeCloseTo(248);
});

const fakeDeps = (failing: string[]) => ({
  load: async (url: string) => {
    if (failing.includes(url)) throw new Error("404");
    return { url } as unknown as never;
  },
  cut: (tex: unknown, box: readonly number[]) => ({ tex, box }) as unknown as never,
});

test("all sprites load", async () => {
  const r = await loadSkin(skinUrls(DEFAULTS), "1P", fakeDeps([]));
  expect(r.missing).toEqual([]);
  expect(r.textures).not.toBeNull();
});

test("missing sprite falls back", async () => {
  const urls = skinUrls(DEFAULTS);
  const r = await loadSkin(urls, "1P", fakeDeps([urls.frame]));
  expect(r.textures).toBeNull();
  expect(r.missing).toEqual([urls.frame]);
});

test("optional sprite missing keeps the skin", async () => {
  const urls = skinUrls(DEFAULTS);
  const r = await loadSkin(urls, "1P", fakeDeps([urls.turntable]));
  expect(r.textures).not.toBeNull();
  expect(r.missing).toEqual([urls.turntable]);
});

test("changing the skin folder changes every url", () => {
  const a = skinUrls(DEFAULTS), b = skinUrls({ ...DEFAULTS, skin_dir: "skins/other" });
  for (const k of Object.keys(a) as (keyof typeof a)[]) expect(a[k]).not.toBe(b[k]);
  expect(b.notes.startsWith("/skin/play/parts/notes/default.png")).toBe(true);
});
