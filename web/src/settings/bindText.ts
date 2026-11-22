import type { Source, Target } from "../lib/events";

export function bindPrompt(t: Target): string {
  if (t === "S_up") return "Spin the turntable one way (scratch up)";
  if (t === "S_down") return "Spin it the other way (scratch down)";
  return `Press key ${t}`;
}

export function targetName(t: Target): string {
  return t === "S_up" ? "Scratch up" : t === "S_down" ? "Scratch down" : `Key ${t}`;
}

export function sourceText(s: Source | undefined): string {
  if (!s) return "not bound";
  if (s.kind === "button") return `button ${s.index + 1}`;
  if (s.kind === "axis") return `axis ${s.index + 1} ${s.sign > 0 ? "+" : "−"}`;
  return `hat ${s.index + 1} (${s.mask})`;
}
