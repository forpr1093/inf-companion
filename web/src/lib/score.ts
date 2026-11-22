import type { Difficulty } from "./events";

export const DJ_LEVELS = ["F", "E", "D", "C", "B", "A", "AA", "AAA"] as const;

/** Score lines for E..AAA: ceil(max * k / 9), k = 2..8, max = notes * 2. */
function lines(notes: number): { level: string; line: number }[] {
  const max = notes * 2;
  return DJ_LEVELS.slice(1).map((level, i) => ({ level, line: Math.ceil((max * (i + 2)) / 9) }));
}

export function djLevel(score: number, notes: number): string {
  let level = "F";
  for (const l of lines(notes)) if (score >= l.line) level = l.level;
  return level;
}

/** Nearest DJ-level line and the distance to it, e.g. "AA+170" or "E−78". Ties go to the line below. */
export function djBorder(score: number, notes: number | null): { level: string; diff: number; label: string } | null {
  if (!notes || notes <= 0) return null;
  let best: { level: string; diff: number } | null = null;
  for (const l of lines(notes)) {
    const diff = score - l.line;
    if (!best || Math.abs(diff) < Math.abs(best.diff) || (Math.abs(diff) === Math.abs(best.diff) && diff >= 0)) {
      best = { level: l.level, diff };
    }
  }
  const b = best!;
  return { ...b, label: `${b.level}${b.diff >= 0 ? "+" : "−"}${Math.abs(b.diff)}` };
}

export const DIFF_SHORT: Record<Difficulty, string> = {
  BEGINNER: "B", NORMAL: "N", HYPER: "H", ANOTHER: "A", LEGGENDARIA: "L",
};

export const DIFF_VAR: Record<Difficulty, string> = {
  BEGINNER: "var(--diff-beginner)", NORMAL: "var(--diff-normal)", HYPER: "var(--diff-hyper)",
  ANOTHER: "var(--diff-another)", LEGGENDARIA: "var(--diff-leggendaria)",
};
