import type { Lane } from "../events";

export type LaneColor = "white" | "black" | "scratch";
export interface LaneGeom { lane: Lane; x: number; w: number; color: LaneColor; }

// WMII_FHD widths (spec §5.9): the whole lane is 576 wide.
export const SKIN_W = { scratch: 120, white: 68, black: 52, gap: 4, total: 576 } as const;

const KEYS: Lane[] = ["1", "2", "3", "4", "5", "6", "7"];

export function colorOf(lane: Lane): LaneColor {
  if (lane === "S") return "scratch";
  return Number(lane) % 2 === 0 ? "black" : "white";
}

export function laneLayout(side: "1P" | "2P", width: number, height: number): { lanes: LaneGeom[]; judgeY: number } {
  const k = width / SKIN_W.total;
  const order: Lane[] = side === "1P" ? ["S", ...KEYS] : [...KEYS, "S"];
  let x = 0;
  const lanes = order.map((lane, i) => {
    const color = colorOf(lane);
    const w = SKIN_W[color] * k;
    const g: LaneGeom = { lane, x, w, color };
    x += w + (i < order.length - 1 ? SKIN_W.gap * k : 0);
    return g;
  });
  return { lanes, judgeY: height * 0.88 };
}
