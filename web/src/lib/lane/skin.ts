// Skin notes (spec §5.9). Only the note sprites come from the skin; the rest of the lane is drawn.
// Boxes are [x, y, w, h] in play/parts/notes/<style>.png.
import { Assets, Rectangle, Texture } from "pixi.js";
import type { Lane, Settings } from "../events";

export const SPRITES = {
  note: { s: [94, 0, 90, 19], w: [187, 0, 52, 19], b: [241, 0, 40, 19] },
} as const;

/** Height of a note sprite in skin pixels (the lane is 576 wide). */
export const NOTE_H = 19;

export type SpriteKind = "s" | "w" | "b";

export function spriteKind(lane: Lane): SpriteKind {
  if (lane === "S") return "s";
  return Number(lane) % 2 === 0 ? "b" : "w";
}

export interface SkinUrls { notes: string; }

export function skinUrls(s: Settings): SkinUrls {
  // The folder is in the query so a folder change never reuses cached images.
  const dir = encodeURIComponent(s.skin_dir);
  return { notes: `/skin/play/parts/notes/${encodeURIComponent(s.skin_notes)}.png?dir=${dir}` };
}

export interface SkinTextures { note: Record<SpriteKind, Texture>; }

export interface SkinDeps {
  load: (url: string) => Promise<Texture>;
  cut: (tex: Texture, box: readonly number[]) => Texture;
}

const pixiDeps: SkinDeps = {
  load: url => Assets.load<Texture>(url),
  cut: (tex, [x, y, w, h]) => new Texture({ source: tex.source, frame: new Rectangle(x, y, w, h) }),
};

export async function loadSkin(urls: SkinUrls, deps: SkinDeps = pixiDeps): Promise<{ textures: SkinTextures | null; missing: string[] }> {
  let notes: Texture;
  try {
    notes = await deps.load(urls.notes);
  } catch {
    return { textures: null, missing: [urls.notes] };
  }
  const c = (box: readonly number[]) => deps.cut(notes, box);
  return { textures: { note: { s: c(SPRITES.note.s), w: c(SPRITES.note.w), b: c(SPRITES.note.b) } }, missing: [] };
}
