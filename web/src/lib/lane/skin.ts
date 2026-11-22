// WMII_FHD sprite map (spec §5.9). Boxes are [x, y, w, h] in the source PNGs.
// Positions below are converted from beatoraja's bottom-left origin to top-left,
// inside the 685×1080 lane frame.
import { Assets, Rectangle, Texture } from "pixi.js";
import type { Lane, Settings } from "../events";

type Box = [number, number, number, number];

export const SPRITES = {
  note: { s: [94, 0, 90, 19], w: [187, 0, 52, 19], b: [241, 0, 40, 19] },
  beam: { b: [0, 0, 40, 723], w: [42, 0, 52, 723], s: [96, 0, 90, 723] },
  flash: { w: [0, 0, 63, 92], b: [70, 0, 46, 78] },
  lane: { "1P": [0, 0, 432, 6], "2P": [434, 0, 432, 6] },
  frame: { "1P": [0, 0, 685, 1080], "2P": [717, 0, 685, 1080] },
  turntable: { label: [0, 0, 49, 49] },
} as const satisfies Record<string, Record<string, Box>>;

export const FRAME = { w: 685, h: 1080 } as const;

/** Where things sit inside the frame (top-left origin), from the skin's positions.lua. */
const PLACE = {
  laneX: { "1P": 75, "2P": 35 },
  laneW: 576,
  judgeY: 1080 - 287,
  disc: { "1P": 65, "2P": 65 + 431, y: 1080 - 154 - 123, size: 123 },
  label: { "1P": 103, "2P": 103 + 431, y: 1080 - 191 - 49, size: 49 },
  // Key flash: drawn just under the judge line, slightly wider than the note.
  flash: { w: { dx: { "1P": -7, "2P": -9 }, top: 1080 - (287 - 97) - 92, w: 82, h: 92 },
           b: { dx: { "1P": -4, "2P": -6 }, top: 1080 - (287 - 80) - 78, w: 60, h: 78 } },
} as const;

export function frameGeometry(side: "1P" | "2P", frameW: number) {
  const s = frameW / FRAME.w;
  return {
    scale: s,
    laneX: PLACE.laneX[side] * s,
    laneW: PLACE.laneW * s,
    judgeY: PLACE.judgeY * s,
    disc: { x: PLACE.disc[side] * s, y: PLACE.disc.y * s, size: PLACE.disc.size * s },
    label: { x: PLACE.label[side] * s, y: PLACE.label.y * s, size: PLACE.label.size * s },
    flash: {
      w: { dx: PLACE.flash.w.dx[side] * s, top: PLACE.flash.w.top * s, w: PLACE.flash.w.w * s, h: PLACE.flash.w.h * s },
      b: { dx: PLACE.flash.b.dx[side] * s, top: PLACE.flash.b.top * s, w: PLACE.flash.b.w * s, h: PLACE.flash.b.h * s },
    },
  };
}

export type SpriteKind = "s" | "w" | "b";

export function spriteKind(lane: Lane): SpriteKind {
  if (lane === "S") return "s";
  return Number(lane) % 2 === 0 ? "b" : "w";
}

export interface SkinUrls { notes: string; beam: string; flash: string; lane: string; frame: string; turntable: string; }

export function skinUrls(s: Settings): SkinUrls {
  // The folder is in the query so a folder change never reuses cached images.
  const dir = encodeURIComponent(s.skin_dir);
  const p = (folder: string, stem: string) => `/skin/play/parts/${folder}/${encodeURIComponent(stem)}.png?dir=${dir}`;
  return {
    notes: p("notes", s.skin_notes),
    beam: p("laser", s.skin_beam),
    flash: p("keyflash", s.skin_flash),
    lane: p("lane", s.skin_lane),
    frame: p("frame/Wide", s.skin_frame),
    turntable: p("turntable", s.skin_turntable),
  };
}

export interface SkinTextures {
  frame: Texture;
  lane: Texture | null;
  note: Record<SpriteKind, Texture>;
  beam: Record<SpriteKind, Texture>;
  flash: Record<"w" | "b", Texture> | null;
  label: Texture | null;
}

export interface SkinDeps {
  load: (url: string) => Promise<Texture>;
  cut: (tex: Texture, box: readonly number[]) => Texture;
}

const pixiDeps: SkinDeps = {
  load: url => Assets.load<Texture>(url),
  cut: (tex, [x, y, w, h]) => new Texture({ source: tex.source, frame: new Rectangle(x, y, w, h) }),
};

/** Load the skin. Notes, beam and frame are required; without them textures is null. */
export async function loadSkin(urls: SkinUrls, side: "1P" | "2P", deps: SkinDeps = pixiDeps): Promise<{ textures: SkinTextures | null; missing: string[] }> {
  const missing: string[] = [];
  const get = async (url: string) => {
    try { return await deps.load(url); } catch { missing.push(url); return null; }
  };
  const [notes, beam, frame, flash, lane, turntable] = await Promise.all(
    [urls.notes, urls.beam, urls.frame, urls.flash, urls.lane, urls.turntable].map(get),
  );
  if (!notes || !beam || !frame) return { textures: null, missing };
  const c = (t: Texture, box: readonly number[]) => deps.cut(t, box);
  return {
    missing,
    textures: {
      frame: c(frame, SPRITES.frame[side]),
      lane: lane ? c(lane, SPRITES.lane[side]) : null,
      note: { s: c(notes, SPRITES.note.s), w: c(notes, SPRITES.note.w), b: c(notes, SPRITES.note.b) },
      beam: { s: c(beam, SPRITES.beam.s), w: c(beam, SPRITES.beam.w), b: c(beam, SPRITES.beam.b) },
      flash: flash ? { w: c(flash, SPRITES.flash.w), b: c(flash, SPRITES.flash.b) } : null,
      label: turntable ? c(turntable, SPRITES.turntable.label) : null,
    },
  };
}
