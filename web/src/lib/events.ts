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
}

export const DEFAULTS: Settings = {
  side: "1P",
  manual_bpm: 150,
  beats_per_loop: 4,
  theme: "dark",
};

export type Difficulty = "BEGINNER" | "NORMAL" | "HYPER" | "ANOTHER" | "LEGGENDARIA";

/** title is null when the song isn't in the recognition tables yet. */
export interface Chart { title: string | null; artist: string | null; difficulty: Difficulty; level: number | null; bpm: number | null; notes: number | null; }

export interface PersonalBest {
  score: number; notes: number | null; lamp: string; miss_count: number | null;
  last_played: string | null; source: "official" | "local";
}

export interface RecentPlay {
  title: string; difficulty: Difficulty; level: number | null; score: number; notes: number | null;
  option: string | null; played_at: string;
}

export type Screen = "music_select" | "play" | "result" | "loading" | "screentransition" | "entry" | "gameend" | "unknown";
export interface CaptureStatus { state: "running" | "no frames" | "off"; message?: string; }

export interface KeyEvent { type: "key_down" | "key_up"; lane: Lane; dir: "up" | "down" | null; t: number; at: number; }

export type ServerEvent =
  | { type: "hello"; at: number; version: string; settings: Settings; devices: DeviceInfo[]; bindings: Record<string, Binding>; has_gif: boolean; counts: Counts;
      binding: { target: Target; index: number; total: number } | null; gif_version: number;
      screen: Screen | null; capture_status: CaptureStatus; chart?: Chart | null; personal_best?: PersonalBest | null;
      recent_plays?: RecentPlay[] }
  | { type: "settings"; at: number; settings: Settings }
  | { type: "devices"; at: number; devices: DeviceInfo[] }
  | KeyEvent
  | { type: "bind_step"; at: number; target: Target; index: number; total: number }
  | { type: "bind_done"; at: number; binding: Binding }
  | { type: "bind_cancelled"; at: number }
  | { type: "gif"; at: number; version: number }
  | { type: "counts"; at: number; counts: Counts }
  | { type: "error"; at: number; message: string }
  | { type: "chart"; at: number; chart: Chart | null }
  | { type: "personal_best"; at: number; best: PersonalBest | null }
  | { type: "recent_plays"; at: number; plays: RecentPlay[] }
  | { type: "screen"; at: number; screen: Screen }
  | ({ type: "capture_status"; at: number } & CaptureStatus);

export function emptyCounts(): Counts {
  return Object.fromEntries(TARGETS.map(t => [t, 0])) as Counts;
}
