import { writable, get } from "svelte/store";
import { connect, type Status } from "./ws";
import { applyKey } from "./counter/counts";
import { DEFAULTS, emptyCounts, type CaptureStatus, type Screen, type Chart, type PersonalBest, type RecentPlay, type Binding, type Counts, type DeviceInfo, type KeyEvent, type ServerEvent, type Settings, type Target } from "./events";

export const status = writable<Status>("connecting");
export const settings = writable<Settings>({ ...DEFAULTS });
export const devices = writable<DeviceInfo[]>([]);
export const bindings = writable<Record<string, Binding>>({});
export const hasGif = writable(false);
export const gifVersion = writable(0);
export const bindProgress = writable<{ target: Target; index: number; total: number } | null>(null);
export const counts = writable<Counts>(emptyCounts());
export const lastError = writable<string | null>(null);
export const screen = writable<Screen | null>(null);
export const captureStatus = writable<CaptureStatus>({ state: "off" });
export const nowPlaying = writable<Chart | null>(null);
/** Best for the current chart; null means not played yet (or no chart). */
export const personalBest = writable<PersonalBest | null>(null);
export const recentPlays = writable<RecentPlay[]>([]);

// Key events are too frequent for Svelte stores: plain pub/sub.
type KeyFn = (e: KeyEvent) => void;
const keyListeners = new Set<KeyFn>();
const resetListeners = new Set<() => void>();
const eventListeners = new Set<(e: ServerEvent) => void>();

export function emitKey(e: KeyEvent): void {
  if (e.type === "key_down") counts.update(c => applyKey(c, e));
  for (const fn of keyListeners) fn(e);
}
export function subscribeKeys(fn: KeyFn): () => void { keyListeners.add(fn); return () => keyListeners.delete(fn); }
export function subscribeReset(fn: () => void): () => void { resetListeners.add(fn); return () => resetListeners.delete(fn); }
export function subscribeEvents(fn: (e: ServerEvent) => void): () => void { eventListeners.add(fn); return () => eventListeners.delete(fn); }
export function emitReset(): void { for (const fn of resetListeners) fn(); }

/** Apply one server event to the stores. Exported for tests. */
export function applyEvent(e: ServerEvent): void {
  switch (e.type) {
    case "hello":
      settings.set(e.settings); devices.set(e.devices); bindings.set(e.bindings);
      hasGif.set(e.has_gif); counts.set(e.counts); bindProgress.set(e.binding ?? null);
      gifVersion.set(e.gif_version ?? 0);
      screen.set(e.screen ?? null); captureStatus.set(e.capture_status ?? { state: "off" });
      // Only a real chart replaces what's shown (a null keeps demo data on ?demo pages).
      if (e.chart) { nowPlaying.set(e.chart); personalBest.set(e.personal_best ?? null); }
      if (e.recent_plays?.length) recentPlays.set(e.recent_plays);
      break;
    case "settings": settings.set(e.settings); break;
    case "devices": devices.set(e.devices); break;
    case "key_down": case "key_up": emitKey(e); break;
    case "bind_step": bindProgress.set({ target: e.target, index: e.index, total: e.total }); break;
    case "bind_done":
      bindProgress.set(null);
      bindings.update(b => ({ ...b, [e.binding.device_guid]: e.binding }));
      break;
    case "bind_cancelled": bindProgress.set(null); break;
    case "gif": hasGif.set(true); gifVersion.set(e.version); break;
    case "counts": counts.set(e.counts); break;
    case "error": lastError.set(e.message); break;
    case "chart": nowPlaying.set(e.chart); break;
    case "personal_best": personalBest.set(e.best); break;
    case "recent_plays": recentPlays.set(e.plays); break;
    case "screen": screen.set(e.screen); break;
    case "capture_status": {
      const { type: _t, at: _a, ...status } = e;
      captureStatus.set(status);
      break;
    }
  }
  for (const fn of eventListeners) fn(e);
}

let conn: ReturnType<typeof connect> | null = null;

export function startConnection(url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`): void {
  if (conn) return;
  conn = connect(url, { onEvent: applyEvent, onStatus: s => status.set(s), onReset: emitReset });
}

export function send(msg: object): void { conn?.send(msg); }

export async function patchSettings(patch: Partial<Settings>): Promise<void> {
  const r = await fetch("/api/settings", {
    method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(patch),
  });
  const body = await r.json();
  if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
  settings.set(body);
}

export { get };

/** Upload a GIF (raw body). Throws with the server's message on 4xx. */
export async function uploadGif(file: File): Promise<void> {
  const r = await fetch("/api/gif", { method: "PUT", headers: { "content-type": "image/gif" }, body: file });
  if (!r.ok) {
    let msg = `Upload failed (HTTP ${r.status})`;
    try { msg = (await r.json()).error ?? msg; } catch { /* keep default */ }
    throw new Error(msg);
  }
}
