// Wire protocol shared with the Python server (see the plan's "Wire protocol" table).

export type Lane = "S" | "1" | "2" | "3" | "4" | "5" | "6" | "7";
export type Target = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "S_up" | "S_down";
export const TARGETS: Target[] = ["1", "2", "3", "4", "5", "6", "7", "S_up", "S_down"];

export type Counts = Record<Target, number>;

export type Source =
  | { kind: "button"; index: number; sign: number; mask: number }
  | { kind: "axis"; index: number; sign: number; mask: number }
  | { kind: "hat"; index: number; sign: number; mask: number };

export interface Binding { device_guid: string; name: string; map: Partial<Record<Target, Source>>; }
export interface DeviceInfo { guid: string; name: string; bound: boolean; }

export interface Settings {
  side: "1P" | "2P";
  manual_bpm: number;
  beats_per_loop: number;
  theme: "dark" | "light";
  skin_dir: string;
  skin_notes: string;
}

export const DEFAULTS: Settings = {
  side: "1P",
  manual_bpm: 150,
  beats_per_loop: 4,
  theme: "dark",
  skin_dir: "skins/WMII_FHD",
  skin_notes: "default",
};

export interface KeyEvent { type: "key_down" | "key_up"; lane: Lane; dir: "up" | "down" | null; t: number; at: number; }

export type ServerEvent =
  | { type: "hello"; at: number; version: string; settings: Settings; devices: DeviceInfo[]; bindings: Record<string, Binding>; has_gif: boolean; counts: Counts }
  | { type: "settings"; at: number; settings: Settings }
  | { type: "devices"; at: number; devices: DeviceInfo[] }
  | KeyEvent
  | { type: "bind_step"; at: number; target: Target; index: number; total: number }
  | { type: "bind_done"; at: number; binding: Binding }
  | { type: "bind_cancelled"; at: number }
  | { type: "gif"; at: number; version: number }
  | { type: "counts"; at: number; counts: Counts }
  | { type: "error"; at: number; message: string };

export function emptyCounts(): Counts {
  return Object.fromEntries(TARGETS.map(t => [t, 0])) as Counts;
}
