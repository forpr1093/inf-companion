import type { Lane } from "../events";

/** One drawn note. Positions are fractions of the travel: 0 = judge line, 1 = top of the lane. */
export interface NoteView { lane: Lane; top: number; bottom: number; alpha: number; }

interface Note { lane: Lane; pressT: number; releaseT: number | null; }

export type Dir = "up" | "down" | null;

export interface NoteFieldOptions { riseMs?: number; fadeFrom?: number; maxNotes?: number; }

const FLASH_MS = 120;

/**
 * Notes that appear on a press and float up. While a key is held the note grows from the
 * judge line; on release it rises at 1/riseMs and fades out near the top.
 */
export class NoteField {
  readonly riseMs: number;
  readonly fadeFrom: number;
  readonly maxNotes: number;
  private notes: Note[] = [];
  private held = new Map<Lane, Note>();
  private lastPress = new Map<Lane, number>();
  private dirs = new Map<Lane, Dir[]>(); // held directions per lane, newest last

  constructor(opts: NoteFieldOptions = {}) {
    this.riseMs = opts.riseMs ?? 900;
    this.fadeFrom = opts.fadeFrom ?? 0.7;
    this.maxNotes = opts.maxNotes ?? 256;
  }

  /**
   * Start a note. `dir` tells the two scratch directions apart: each direction is held on
   * its own, the newest one owns the growing note.
   */
  press(lane: Lane, t: number, dir: Dir = null): void {
    const stack = (this.dirs.get(lane) ?? []).filter(d => d !== dir);
    stack.push(dir);
    this.dirs.set(lane, stack);
    this.startNote(lane, t);
  }

  /**
   * Release one direction. Releasing a direction that isn't the newest one does nothing
   * visible; releasing the newest hands the hold back to a direction still held.
   */
  release(lane: Lane, t: number, dir: Dir = null): void {
    const stack = this.dirs.get(lane);
    if (!stack || !stack.includes(dir)) return;
    const wasActive = stack[stack.length - 1] === dir;
    stack.splice(stack.indexOf(dir), 1);
    if (!wasActive) return;
    this.endNote(lane, t);
    if (stack.length > 0) this.startNote(lane, t);
    else this.dirs.delete(lane);
  }

  releaseAll(t: number): void {
    for (const n of this.held.values()) n.releaseT = t;
    this.held.clear();
    this.dirs.clear();
  }

  /** The direction that owns the current hold, or null. */
  activeDir(lane: Lane): Dir {
    const stack = this.dirs.get(lane);
    return stack && stack.length ? stack[stack.length - 1] : null;
  }

  private startNote(lane: Lane, t: number): void {
    this.endNote(lane, t);
    const n: Note = { lane, pressT: t, releaseT: null };
    this.notes.push(n);
    this.held.set(lane, n);
    this.lastPress.set(lane, t);
    if (this.notes.length > this.maxNotes) {
      const dropped = this.notes.shift()!;
      if (this.held.get(dropped.lane) === dropped) this.held.delete(dropped.lane);
    }
  }

  private endNote(lane: Lane, t: number): void {
    const n = this.held.get(lane);
    if (!n) return;
    n.releaseT = t;
    this.held.delete(lane);
  }

  isHeld(lane: Lane): boolean { return this.held.has(lane); }

  frame(t: number): NoteView[] {
    const out: NoteView[] = [];
    const keep: Note[] = [];
    for (const n of this.notes) {
      let bottom: number, top: number;
      if (n.releaseT === null) {
        bottom = 0;
        top = Math.min(Math.max(t - n.pressT, 0) / this.riseMs, 1);
      } else {
        const len = Math.min(Math.max(n.releaseT - n.pressT, 0) / this.riseMs, 1);
        bottom = Math.max(t - n.releaseT, 0) / this.riseMs;
        top = bottom + len;
      }
      if (bottom >= 1) continue;
      keep.push(n);
      const alpha = bottom <= this.fadeFrom ? 1 : Math.max(0, 1 - (bottom - this.fadeFrom) / (1 - this.fadeFrom));
      out.push({ lane: n.lane, top, bottom, alpha });
    }
    this.notes = keep;
    return out;
  }

  flashes(t: number): { lane: Lane; alpha: number }[] {
    const out: { lane: Lane; alpha: number }[] = [];
    for (const [lane, pt] of this.lastPress) {
      const age = t - pt;
      if (age >= FLASH_MS) { this.lastPress.delete(lane); continue; }
      out.push({ lane, alpha: 1 - Math.max(age, 0) / FLASH_MS });
    }
    return out;
  }
}
