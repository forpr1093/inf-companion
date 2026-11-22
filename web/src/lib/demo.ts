// Fake key input for designing the page without a controller (?demo=1),
// and a keyboard stand-in for quick checks (?dev=1).
import type { KeyEvent, Lane } from "./events";

type Emit = (e: KeyEvent) => void;

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const KEYS: Lane[] = ["1", "2", "3", "4", "5", "6", "7"];

function key(type: KeyEvent["type"], lane: Lane, dir: KeyEvent["dir"]): KeyEvent {
  const now = typeof performance !== "undefined" ? performance.now() : Date.now();
  return { type, lane, dir, t: now, at: Date.now() };
}

/** Seeded stream of 16th-note presses, chords, holds and scratches. Returns stop(). */
export function startDemo(emit: Emit, opts: { seed?: number; bpm?: number } = {}): () => void {
  const rand = mulberry32(opts.seed ?? 1);
  const stepMs = 60000 / (opts.bpm ?? 150) / 4;
  const held = new Map<string, { lane: Lane; dir: KeyEvent["dir"]; timer: ReturnType<typeof setTimeout> }>();
  let step = 0;
  let scratchDir: "up" | "down" = "up";

  const press = (lane: Lane, dir: KeyEvent["dir"], holdMs: number) => {
    const id = `${lane}:${dir}`;
    if (held.has(id)) return;
    emit(key("key_down", lane, dir));
    const timer = setTimeout(() => {
      held.delete(id);
      emit(key("key_up", lane, dir));
    }, holdMs);
    held.set(id, { lane, dir, timer });
  };

  const interval = setInterval(() => {
    step += 1;
    const onBeat = step % 4 === 0;
    const r = rand();
    if (r < (onBeat ? 0.85 : 0.5)) {
      const chord = rand() < 0.2 ? 2 + Math.floor(rand() * 2) : 1;
      for (let i = 0; i < chord; i++) {
        const lane = KEYS[Math.floor(rand() * KEYS.length)];
        press(lane, null, rand() < 0.1 ? stepMs * 4 : 45 + rand() * 40);
      }
    }
    if (rand() < 0.12) {
      if (rand() < 0.5) scratchDir = scratchDir === "up" ? "down" : "up";
      press("S", scratchDir, stepMs * (1 + Math.floor(rand() * 3)));
    }
  }, stepMs);

  return () => {
    clearInterval(interval);
    for (const { lane, dir, timer } of held.values()) {
      clearTimeout(timer);
      emit(key("key_up", lane, dir));
    }
    held.clear();
  };
}

/** Keyboard → lane, for ?dev=1. Shift and A scratch; Z S X D C F V are keys 1–7. */
export const devKeyboardMap: Record<string, { lane: Lane; dir: KeyEvent["dir"] }> = {
  ShiftLeft: { lane: "S", dir: "up" },
  KeyA: { lane: "S", dir: "down" },
  KeyZ: { lane: "1", dir: null },
  KeyS: { lane: "2", dir: null },
  KeyX: { lane: "3", dir: null },
  KeyD: { lane: "4", dir: null },
  KeyC: { lane: "5", dir: null },
  KeyF: { lane: "6", dir: null },
  KeyV: { lane: "7", dir: null },
};

export function devKeyboard(emit: Emit): () => void {
  const onKey = (down: boolean) => (e: KeyboardEvent) => {
    const m = devKeyboardMap[e.code];
    if (!m || e.repeat) return;
    e.preventDefault();
    emit(key(down ? "key_down" : "key_up", m.lane, m.dir));
  };
  const kd = onKey(true), ku = onKey(false);
  window.addEventListener("keydown", kd);
  window.addEventListener("keyup", ku);
  return () => { window.removeEventListener("keydown", kd); window.removeEventListener("keyup", ku); };
}
