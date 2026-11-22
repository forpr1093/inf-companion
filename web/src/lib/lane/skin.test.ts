import { expect, test } from "vitest";
import { DEFAULTS, type Lane } from "../events";
import { loadSkin, skinUrls, spriteKind } from "./skin";

test("skin urls carry note style and folder", () => {
  const u = skinUrls({ ...DEFAULTS, skin_notes: "pastel" });
  expect(u).toEqual({ notes: "/skin/play/parts/notes/pastel.png?dir=skins%2FWMII_FHD" });
});

test("changing the skin folder changes the url", () => {
  expect(skinUrls(DEFAULTS).notes).not.toBe(skinUrls({ ...DEFAULTS, skin_dir: "skins/other" }).notes);
});

test("sprite kind per lane", () => {
  expect(["S", "1", "2", "7"].map(l => spriteKind(l as Lane))).toEqual(["s", "w", "b", "w"]);
});

const fakeDeps = (failing: string[]) => ({
  load: async (url: string) => {
    if (failing.includes(url)) throw new Error("404");
    return { url } as unknown as never;
  },
  cut: (tex: unknown, box: readonly number[]) => ({ tex, box }) as unknown as never,
});

test("notes load and are cut into three sprites", async () => {
  const r = await loadSkin(skinUrls(DEFAULTS), fakeDeps([]));
  expect(r.missing).toEqual([]);
  expect(Object.keys(r.textures!.note).sort()).toEqual(["b", "s", "w"]);
});

test("missing sprite falls back", async () => {
  const urls = skinUrls(DEFAULTS);
  const r = await loadSkin(urls, fakeDeps([urls.notes]));
  expect(r.textures).toBeNull();
  expect(r.missing).toEqual([urls.notes]);
});
