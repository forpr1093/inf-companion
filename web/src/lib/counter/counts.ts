import { emptyCounts, type Counts, type KeyEvent, type Target } from "../events";

export { emptyCounts };

export function counterTarget(e: KeyEvent): Target {
  if (e.lane === "S") return e.dir === "down" ? "S_down" : "S_up";
  return e.lane;
}

/** +1 for a key_down. Scratch counts by direction. Returns a new object. */
export function applyKey(c: Counts, e: KeyEvent): Counts {
  if (e.type !== "key_down") return { ...c };
  const t = counterTarget(e);
  return { ...c, [t]: c[t] + 1 };
}
